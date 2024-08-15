import copy 
import logging

from datetime import datetime

from typing import List, Optional

from fastapi import (
    APIRouter, 
    Depends
)

import numpy as np

from azure.storage.blob import BlobServiceClient

from openai import AsyncOpenAI
from voyageai import Client as VoyageClient
    

from SolwayAPI.api.v1.core.config import settings
from SolwayAPI.api.v1.core.skill_prompts import rq_answering, role

from SolwayAPI.api.v1.models.skillchain_models import Skill 

from SolwayAPI.api.v1.core.utils.skillchain_helpers import make_open_ai_request

from .skillchain import (
    get_oai_client
)

from .artifacts import (
    get_voyage_ai_client
)

from .blobstorage import (
    get_az_blob_storage_client,
    create_blob,
    get_blob, 
)

from .notion import create_child_notion_page



class Retriever:

    def __init__(self, index):
        
        self.chunks2idx = {idx:chunk for idx, chunk in enumerate(index['textstore'])}
        self.embs2idx = {idx:emb for idx, emb in enumerate(index['vectorstore'])}
        self.vector_store = {idx:np.array(emb) for idx, emb in self.embs2idx.items()}


    def populate_prompt(self, skill:Skill, agent_internals:dict) -> str:
        """ swaps the dummy symbols in the skill prompt with the generated replacements """
        full_prompt = skill.role + skill.instructions
        for _, value in agent_internals.items():
            full_prompt = full_prompt.replace(value['marker'], value['replacement'])
        return full_prompt


    def cosine_similarity(self, a, b):
        """ similarity metrics to compare embeddings"""
        return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))


    async def __call__(self, oai_client:AsyncOpenAI, vo_client:VoyageClient, sys_prompt:str, queries:List[str], top_n:int) -> None:
        """ answers each research question in the proposal, writest oaj  son"""
        
        q_embs = vo_client.embed(queries, model="voyage-large-2-instruct", input_type="document").embeddings

        responses = []
        for idx, question in enumerate(queries):

            # Calculate similarity between the user question & each chunk
            similarities = [self.cosine_similarity(q_embs[idx], chunk) for chunk in self.embs2idx.values()]
            sorted_indices = np.argsort(similarities)[::-1]
            top_indices = sorted_indices[:top_n]
            top_chunks_after_retrieval = [self.chunks2idx[i] for i in top_indices]
    
            usr_msg = ''
            for chunk in top_chunks_after_retrieval:
                usr_msg += f"!!! START CHUNK !!! DOCUMENT NAME TO REFERENCE: {chunk.get('title')} PAGE NUMBER TO REFERENCE: {chunk.get('page_number')} DOCUMENT TEXT: {chunk.get('text')} !!! END CHUNK !!!"

            sys_prompt = sys_prompt.replace("?", question)

            print(sys_prompt)
            response = await make_open_ai_request(oai_client, sys_prompt, usr_msg)
            responses.append(response.choices[0].message.content)
        
        return {q:r for q, r in zip(queries, responses)}



rq_skill = Skill(
    name='rq_answering',
    role=role,
    instructions=rq_answering,
    contiguous_on='',
    output=''
)


router = APIRouter(tags=['retrieval'])


@router.post("/") 
async def retrieval_aug_gen(
    project_folder_name:str, 
    top_n:int=30,
    notion_page_id:Optional[str]='',
    overwrite:Optional[bool]=False, 
    oai_client:AsyncOpenAI=Depends(get_oai_client),
    vo_client:VoyageClient=Depends(get_voyage_ai_client),
    blob_client:BlobServiceClient=Depends(get_az_blob_storage_client)):   
    """ Performs RAG \n
    
    notion_page_id: b38df40ef7fa49678bbb069a71203eb3

    project_folder_name: city_of_kelowna/sub_project_1 \n
    
    """
    
    context_content = await get_blob(
        f"{project_folder_name}/{settings.TMP_FOLDER}/{settings.CONTEXT_FILE_NAME}", 
        service_client=blob_client
    )

    context = list(context_content.values()).pop()

    logging.info(context['context'].get("research_questions"))

    index_content = await get_blob(
        f"{project_folder_name}/{settings.TMP_FOLDER}/{settings.INDEX_FILE_NAME}", 
        service_client=blob_client
    )

    index = list(index_content.values()).pop()

    retriever = Retriever(index)
    sys_prompt = retriever.populate_prompt(copy.deepcopy(rq_skill), context['agent_internals'])

    questions = context['context']['research_questions'].split("\n")
    questions = [q.strip('- ') for q in questions[1:] if q]

    answers = await retriever(
        oai_client=oai_client, 
        vo_client=vo_client, 
        sys_prompt=sys_prompt, 
        queries=questions, 
        top_n=top_n
    )
    
    await create_blob(
        blob_name=f"{project_folder_name}/{settings.TMP_FOLDER}/research_questions.json",
        content=answers,
        overwrite=overwrite,
        service_client=blob_client
    )

    created_page_ids = []
    if notion_page_id:
        for question, answer in answers.items():
            created_page_id = await create_child_notion_page(parent_id=notion_page_id, title=question, content=answer)
            created_page_ids.append(created_page_id)


    return {
        "created_notion_pages": created_page_ids,
        "content": answers,
        "created_at": str(datetime.now())
    }



