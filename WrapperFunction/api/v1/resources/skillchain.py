import os
import json
import copy

from typing import Dict, List, Union

from fastapi import (
    APIRouter, 
    Depends
)

import tiktoken
from openai import AsyncOpenAI

from v1.core.config import settings
from v1.core.clients import get_openai_client

from v1.models.skillchain_models import Skill

from v1.resources.skillchain_helpers import (
    chunk_document_naive,
    make_open_ai_request,
)

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


class SkillChain:

    def __init__(self):
        
        self.encoding = tiktoken.get_encoding(encoding_name="cl100k_base")


    def populate_prompt(self, skill:Skill, agent_internals:dict) -> str:
        """
        swaps the dummy symbols in the skill prompt with the generated replacements
        """
        full_prompt = skill.role + skill.instructions
        for _, value in agent_internals.items():
            full_prompt = full_prompt.replace(value['marker'], value['replacement'])
        return full_prompt


    def get_document(self, folder_name, file_name) -> Union[dict, None]:
        """ reads a parsed file from the hosts disk """
        try:
            documents = json.load(open(f"{folder_name}/{settings.PROJECT_DOCS_PROCESSED_NAME}"))
            print(documents.keys())
            return documents.get(file_name, '')
        except Exception as e:
            print(f"Unexpected Exception: {e}")


    def contiguous_generation(base_prompt:str, replacement:str, marker:str='*') -> str:
        """ replaces a component of a prompt, with a previous generation"""
        return base_prompt.replace(marker, replacement)


    async def create_skill_completion(self, client:AsyncOpenAI, skill_completions:dict, name:str, document:dict, prompt:str, output_folder:str, model:str, token_thresh:int, overwrite_skills:bool, contiguous_on:str=None):
        """ calls gpt-4 with a skill prompt on a document """
    
        if not os.path.exists(output_folder):
            os.makedirs(output_folder, exist_ok=True)

        num_tokens = 0
        text = ''
        for page, data in document.items():
            num_tokens += int(data.get('numTokens'))
            text += f"""!!! START PAGE {page} !!! PAGE TEXT: {data.get('textIN')} !!!"""

        if int(num_tokens) > token_thresh:
            chunks = chunk_document_naive(self.encoding, text)        
            text = [skill_completions['summarization'] + self.encoding.decode(chunk) for chunk in chunks]

        if contiguous_on:
            prompt = self.contiguous_generation(prompt, str(skill_completions[contiguous_on]))
        
        oai_responses = []

        if isinstance(text, str):            
            oai_response = await make_open_ai_request(client, prompt, text, model)            
            response = oai_response.choices[0].message.content
        
        elif isinstance(text, list):
            print("list")
            for chunk in text:
                oai_response = await make_open_ai_request(prompt, chunk, model)
                oai_responses.append(oai_response)
            
            try:
                response = '\n\n'.join([resp.choices[0].message.content for resp in oai_responses if 'sorry' not in resp.choices[0].message.content])
            except Exception as e:
                print(f"Unexpected Error: {e}")
            
        
        if not os.path.exists(f'{output_folder}/{name}.json') or overwrite_skills:
            with open(f'{output_folder}/{name}.json', 'w') as outF:
                document = {
                    "document": name,
                    "textIN": text,
                    "openai_response": [resp.model_dump_json() for resp in oai_responses] if len(oai_responses) > 0 else oai_response.model_dump_json() 
                }
                json.dump(document, outF)
            
        return response


    async def __call__(
        self, 
        client:AsyncOpenAI,
        skills:Union[List[str], str],
        context:dict,
        file_name:str,
        output_folder_name:str,
        overwrite_skills:bool=False) -> Dict[str, str]:
        """ runs the key functions of the class """

        skill_completions = {k.name:copy.deepcopy(k) for k in settings.SKILLS if k.name in skills}
        
        if not context.get("agent_internals"):
            raise ContextError
                
        document = self.get_document(output_folder_name, file_name)
        if not document:
            raise DocumentError(missing_document=file_name)
        
        print(document.keys())
        
        for skill in settings.SKILLS:
            if skill.name in skills:
                completion = await self.create_skill_completion(
                    client=client,
                    skill_completions=skill_completions,
                    name=file_name, 
                    document=document,
                    prompt=self.populate_prompt(skill, context.get("agent_internals")), 
                    overwrite_skills=overwrite_skills, 
                    contiguous_on=skill.contiguous_on if skill.contiguous_on else None,
                    model=settings.FOUNDATION_MODEL, 
                    token_thresh=settings.NAIVE_CHUNK_THRESHOLD,
                    output_folder=output_folder_name+"/skills/"+skill.name, 
                )

                skill_completions[skill.name].output = completion
            
        return skill_completions


router = APIRouter(tags=['skillchain'])

def get_oai_client(client:AsyncOpenAI=Depends(get_openai_client)):
    return client


@router.post("/") 
async def get_skills(
    skills:Union[List[str], str],
    context:dict, 
    file_name:str,
    output_folder_name:str, 
    overwrite_skills:bool=False, 
    client:AsyncOpenAI=Depends(get_oai_client)) -> dict:   
    """
    Third step in the Chain is to run the skills
    returns this information as JSON and writes to the disk of the host 
    """
    return await SkillChain()(
        client=client,
        file_name=file_name, 
        skills=skills,
        context=context,
        output_folder_name=settings.PROJECT_DATA_FOLDER+output_folder_name, 
        overwrite_skills=overwrite_skills, 
    )


