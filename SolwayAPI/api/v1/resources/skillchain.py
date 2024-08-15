import copy
import logging 

from pathlib import Path

from datetime import datetime

from typing import Dict, List, Union, Optional

from fastapi import (
    APIRouter, 
    Depends
)

from openai import AsyncOpenAI

from azure.storage.blob import BlobServiceClient

from SolwayAPI.api.v1.core.config import settings
from SolwayAPI.api.v1.core.clients import get_openai_client
from SolwayAPI.api.v1.models.skillchain_models import Skill

from SolwayAPI.api.v1.core.utils.blobstorage_helpers import get_file_name
from SolwayAPI.api.v1.core.utils.skillchain_helpers import (
    chunk_document_naive,
    make_open_ai_request,
)

from .notion import create_child_notion_page


from .blobstorage import (
    get_az_blob_storage_client,
    get_blob, 
    create_blob
)


logging.basicConfig(level=logging.INFO)


class ContextError(Exception):
    def __init__(self, message="Could not Read Agent Internals: "):
            self.message = message 
            super().__init__(self.message)


class DocumentError(Exception):
    def __init__(self, message="Could not Read Document: ", missing_document:str=''):
            self.message = message + missing_document
            super().__init__(self.message)


class InvalidSkillError(Exception):
    def __init__(self, message="Skill * not in Skill Prompts, please specify a valid skill", missing_skill:str=''):
            self.message = message.replace('*', missing_skill)
            super().__init__(self.message)

class OAIRequestError(Exception):
    def __init__(self, message="Could Not Succesfully Request OpenAI", missing_skill:str=''):
            self.message = message.replace('*', missing_skill)
            super().__init__(self.message)



class SkillChain:


    def populate_prompt(self, skill:Skill, agent_internals:dict) -> str:
        """ swaps the dummy symbols in the skill prompt with the generated replacements """
        full_prompt = skill.role + skill.instructions
        for _, value in agent_internals.items():
            full_prompt = full_prompt.replace(value['marker'], value['replacement'])
        return full_prompt


    def contiguous_generation(self, base_prompt:str, replacement:str, marker:str='*') -> str:
        """ replaces a component of a prompt, with a previous generation"""
        return base_prompt.replace(marker, replacement)


    async def create_skill_completion(
            self, 
            oai_client:AsyncOpenAI, 
            skill_completions:dict, 
            document:dict, 
            prompt:str, 
            model:str, 
            token_thresh:int, 
            contiguous_on:str=None
        ):
        """ calls OpenAI with a skill prompt on a document """

        text, num_tokens = '', 0
        for page, data in document.items():
            num_tokens += int(data.get('numTokens'))
            text += f"""!!! START PAGE {page} !!! PAGE TEXT: {data.get('textIN')} !!!"""

        if int(num_tokens) > token_thresh:
            chunks = chunk_document_naive(self.encoding, text)        
            text = [skill_completions['summarization'].output + self.encoding.decode(chunk) for chunk in chunks]

        if contiguous_on:
            # we're replacing a special marker within the prompt, 
            prompt = self.contiguous_generation(prompt, skill_completions[contiguous_on].output)
        
        oai_responses = []

        if isinstance(text, str):            
            oai_response = await make_open_ai_request(oai_client, prompt, text, model)            
            response = oai_response.choices[0].message.content
        
        elif isinstance(text, list):

            for chunk in text:
                oai_response = await make_open_ai_request(oai_client, prompt, chunk, model)
                oai_responses.append(oai_response)
            
            try:
                response = '\n\n'.join(
                    [resp.choices[0].message.content for resp in oai_responses if 'sorry' not in resp.choices[0].message.content]
                )
            except Exception as e:
                print(f"Unexpected Error: {e}")
            
        return response


    async def __call__(self, oai_client:AsyncOpenAI, skills:Union[List[str], str], context:dict, document:dict) -> Dict[str, str]:
        """ runs the key functions of the class """

        skill_completions = {k.name:copy.deepcopy(k) for k in settings.SKILLS if k.name in skills}

        for skill in settings.SKILLS:
            if skill.name in skills:
                completion = await self.create_skill_completion(
                    oai_client=oai_client,
                    skill_completions=skill_completions,
                    document=document,
                    prompt=self.populate_prompt(skill, context.get("agent_internals")), 
                    contiguous_on=skill.contiguous_on if skill.contiguous_on else None,
                    model=settings.FOUNDATION_MODEL, 
                    token_thresh=settings.NAIVE_CHUNK_THRESHOLD,
                )

                skill_completions[skill.name].output = completion
            
        return {k:v.model_dump() for k, v in skill_completions.items()}

router = APIRouter(tags=['skillchain'])

def get_oai_client(client:AsyncOpenAI=Depends(get_openai_client)):
    return client


@router.post("/") 
async def generate_skills(
    skills:List[str],
    filename:str,
    project_folder_name:str, 
    overwrite:bool=False, 
    notion_page_id:Optional[str]=None,
    oai_client:AsyncOpenAI=Depends(get_oai_client),
    blob_client:BlobServiceClient=Depends(get_az_blob_storage_client)
    ) -> dict:   
    """
    Third step in the chain is to run the skills
    returns this information as JSON and writes to the disk of the host 

    If notion_page_id is passed, this should correspond to the Documents Page ID, not the Project's ID

    Solway-Development: 845e77c3c0fb4dada255c741da089567
    Solway-Development-azure-functions-test: a7efcd37ad4c41d085f002088b1e7093

    project_folder_name: city_of_kelowna/sub_project_1

    skills: ["summarization", "figures_toc", "action_items", "keypoints", "quotes"]

    file_name: city_of_kelowna/sub_project_1/1184_492.pdf
    """

    context_contents = await get_blob(
        f"{project_folder_name}/{settings.TMP_FOLDER}/{settings.CONTEXT_FILE_NAME}", 
        service_client=blob_client
    )

    context = list(context_contents.values()).pop()
    if not context.get("agent_internals"):
        raise ContextError
    
    file_contents = await get_blob(
        filename, 
        service_client=blob_client
    )

    skill_chain = SkillChain()
    generations = await skill_chain(
        oai_client=oai_client,
        skills=skills,
        context=context,
        document=list(file_contents.values()).pop()
    )

    await create_blob(
        blob_name=f"{project_folder_name}/{settings.TMP_FOLDER}/skills/{Path(get_file_name(filename)).stem}.json",
        content=generations,
        overwrite=True,
        service_client=blob_client
    )

    created_pages = []
    if notion_page_id:
        for skill, generation in generations.items():
            
            page_id = await create_child_notion_page(
                notion_page_id, 
                title=get_file_name(filename), 
                subtitle=skill, 
                content=generation.get('output')
            )
            logging.info(f"Created Notion Page: {skill} - {get_file_name(filename)}: Notion ID: {page_id}")
            created_pages.append(page_id)
    
    return {
        "generations": generations,
        "created_notion_page_ids": created_pages,
        "created_at": str(datetime.now())
    }



@router.post("/completion") 
async def completion(message:str, client:AsyncOpenAI=Depends(get_oai_client)) -> dict:   
    """
    Third step in the Chain is to run the skills
    returns this information as JSON and writes to the disk of the host 

    If notion_page_id is passed, this should correspond to the Documents Page ID, not the Project's ID
    """
    response = await make_open_ai_request(client, "you are a helpful Assistant", message)
    assistant_message = response.choices[0].message.content
    return {
        "completion": assistant_message,
        "created_at": str(datetime.now())
    }

