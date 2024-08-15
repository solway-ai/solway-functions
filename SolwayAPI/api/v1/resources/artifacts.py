import copy
import json
import logging

from typing import Dict, List, Optional

from fastapi import (
    APIRouter, 
    Depends
)

from openai import AsyncOpenAI
from voyageai import Client as VoyageClient


from langchain_core.documents import Document
from langchain_voyageai import VoyageAIEmbeddings
from langchain_experimental.text_splitter import SemanticChunker

from azure.storage.blob import BlobServiceClient

from SolwayAPI.api.v1.core.config import settings

from SolwayAPI.api.v1.core.clients import (
    get_openai_client,
    get_voyage_client
)

from SolwayAPI.api.v1.core.chain_prompts import (
    research_questions,
    thematic_areas,
    context
)


from .blobstorage import (
    get_az_blob_storage_client,
    get_blob, 
    create_blob
)

from ..core.utils.blobstorage_helpers import get_file_name
from ..core.utils.skillchain_helpers import (
    make_open_ai_request,
    update_internals,
    build_string,
    get_all_textIN
)




logging.basicConfig(level=logging.INFO)



router = APIRouter(tags=['artifacts'])


class Indexer:

    def create_chunks_for_index(self, file_name:str, file:Dict[str, Dict[str, str]], text_splitter:SemanticChunker):
        """chunks a document, includes metadata"""
        chunks = text_splitter.split_documents([Document(page_content=page.get('textIN'), metadata={"page_number":idx}) for idx, page in file.items()])
        return [{"text": chunk.page_content, "title":file_name, "page_number": chunk.metadata['page_number']} for chunk in chunks]


    def get_chunk_embeddings(self, vo_client:VoyageClient, chunks:List[dict], batchsize:int) -> list:
        """embeds a list of chunks with the voyager client"""
        batches = [chunk.get("text") for chunk in chunks]
        batches = [batches[step:step+batchsize] for step in range(0, len(batches), batchsize)]

        embeddings = []
        for batch in batches:
            embeddings.append(vo_client.embed(batch, model="voyage-large-2-instruct", input_type="document").embeddings)
        
        return [emb for embs in embeddings for emb in embs]
        
    
    async def __call__(self, vo_client:VoyageClient, file_name:str, file:dict, text_splitter, batchsize:int=100):
        """ runs the key functions of the class """
        text_chunks = self.create_chunks_for_index(file_name, file, text_splitter)
        chunk_embeddings = self.get_chunk_embeddings(vo_client, text_chunks, batchsize)
        return {"chunks":text_chunks, "embeddings": chunk_embeddings}


class Context:

    def __init__(self, internals:dict):
        self.internals = copy.deepcopy(internals)


    async def generate_context(self, oai_client:AsyncOpenAI, context_prompt:str, research_plan:str, max_retries:int=10) -> dict:
        """ get the research questions out of the research documents """
        response = None
        try:
            for i in range(max_retries):
                response = await make_open_ai_request(oai_client, context_prompt, research_plan, response_format={"type": "json_object"})
                return json.loads(response.choices[0].message.content)
        except Exception as e:
            print(e)
            print(response)
            return {"Max Retries Exceed" : "Could not get message content from OpenAI"}
        

    async def __call__(self, oai_client:AsyncOpenAI, research_plan_text:str):
        """ Creates the Context for the Research Project """

        context_dict = {}

        context_dict['research_plan_text'] = research_plan_text

        context_dict['context']  = await self.generate_context(
            oai_client, context, research_plan_text
        )
        
        context_dict['context']['research_questions'] = build_string(
            await self.generate_context(
                oai_client, research_questions, 
                research_plan_text
            )
        )
        
        context_dict['context']['thematic_areas'] = build_string(
            await self.generate_context(
                oai_client, thematic_areas, 
                research_plan_text
            )
        )

        context_dict['agent_internals'] =  update_internals(context_dict['context'], self.internals['agent_internals']) 
        
        return context_dict
        
        


def get_oai_client(client:AsyncOpenAI=Depends(get_openai_client)):
    return client


def get_voyage_ai_client(client:VoyageClient=Depends(get_voyage_client)):
    return client


@router.post("/context") 
async def generate_context(
    proposal_file_name:str, 
    project_folder_name:str, 
    overwrite:Optional[bool]=False, 
    oai_client:AsyncOpenAI=Depends(get_oai_client),
    blob_client:BlobServiceClient=Depends(get_az_blob_storage_client)
    ) -> dict:   
    """
    Second step in the chain is to get the contextualizing information from the RFP, 
    returns this information as a JSON and writes to the disk of the host 

    proposal_file_name="city_of_kelowna/sub_project_1/20240524_KelownaClimateDev_Research Plan vEPR.pdf"
    project_folder_name = "city_of_kelowna/sub_project_1"
    """
    project_context = None
    try:
        context_blob = await get_blob(
            f"{project_folder_name}/{settings.TMP_FOLDER}/{settings.CONTEXT_FILE_NAME}",
            service_client=blob_client
        )
        project_context = list(context_blob.values()).pop()

    except Exception as e:
        logging.info(f"NO CONTEXT FOUND...")

    if not project_context or overwrite:
        blob = await get_blob(
            f"{proposal_file_name}", 
            service_client=blob_client
        )

        project_context = await Context(settings.AGENT_INTERNALS)(
            research_plan_text=get_all_textIN(list(blob.keys()).pop(), list(blob.values()).pop()),
            oai_client=oai_client
        )

        await create_blob(
            blob_name=f"{project_folder_name}/{settings.TMP_FOLDER}/{settings.CONTEXT_FILE_NAME}",
            content=project_context,
            overwrite=overwrite,
            service_client=blob_client
        )

    return project_context



@router.post("/index") 
async def create_index_record(
    project_folder_name:str, 
    file_name:List[str],
    batchsize:Optional[int]=100,
    vo_client:VoyageClient=Depends(get_voyage_ai_client),
    blob_client:BlobServiceClient=Depends(get_az_blob_storage_client)):   
    """ 
    updates the index file
    city_of_kelowna/sub_project_1/1184_492.pdf
    """
    try:
        index_blob = await get_blob(
            f"{project_folder_name}/{settings.TMP_FOLDER}/{settings.INDEX_FILE_NAME}", 
            service_client=blob_client
        )
        index = list(index_blob.values()).pop()

    except Exception as e:
        logging.info(f"NO INDEX FOUND...")
        index = {
            "filenames": [],
            "textstore": [],
            "vectorstore": [],
        }

    assert len(index['textstore']) == len(index['vectorstore'])
    proper_file_name = get_file_name(file_name)

    if proper_file_name not in index['filenames']:
        chunker = SemanticChunker(
            VoyageAIEmbeddings(
                voyage_api_key=settings.VOYAGE_API_KEY, model="voyage-large-2-instruct"
            ),
            breakpoint_threshold_type="percentile"
        )

        file_content = await get_blob(
            file_name, 
            service_client=blob_client
        )

        indexer = Indexer()
        record = await indexer(vo_client, proper_file_name, list(file_content.values()).pop(), chunker, batchsize)

        assert len(record['chunks']) == len(record['embeddings'])

        index['filenames'].append(proper_file_name)
        index['textstore'] += record['chunks']
        index['vectorstore'] += record["embeddings"]

        await create_blob(
            blob_name=f"{project_folder_name}/{settings.TMP_FOLDER}/{settings.INDEX_FILE_NAME}",
            content=index,
            overwrite=True,
            service_client=blob_client
        )
    else:
        logging.info("File already in Index")

    return {'files': index['filenames']}


@router.post("/delete") 
async def delete_index():   
    """ updates the index file"""
    return {}

