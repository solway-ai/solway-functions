import os
import copy
import json

from fastapi import (
    APIRouter, 
    Depends
)

from openai import AsyncOpenAI

from SolwayAPI.api.v1.core.clients import get_openai_client
from SolwayAPI.api.v1.core.config import settings


from SolwayAPI.api.v1.core.chain_prompts import (
    research_questions,
    thematic_areas,
    context
)

from SolwayAPI.api.v1.resources.skillchain_helpers import (
    make_open_ai_request,
    update_internals,
    build_string
)



class Context:

    def __init__(self, internals:dict):
        self.internals = copy.deepcopy(internals)


    async def generate_context(self, client:AsyncOpenAI, context_prompt:str, research_plan:str, max_retries:int=10) -> dict:
        """ get the research questions out of the research documents """
        response = None
        try:
            for i in range(max_retries):
                response = await make_open_ai_request(client, context_prompt, research_plan, response_format={"type": "json_object"})
                return json.loads(response.choices[0].message.content)
        except Exception as e:
            print(e)
            print(response)
            return {"Max Retries Exceed" : "Could not get message content from OpenAI"}
        

    async def create_context(self, client:AsyncOpenAI, output_folder_name:str, research_plan_text:str):
        """ Creates the Context for the Research Project with the """

        if not os.path.exists(output_folder_name):
            print(f"creating {output_folder_name} directory")
            os.makedirs(output_folder_name, exist_ok=True)

        print("generating context")
        context_dict = {}

        context_dict['research_plan_text'] = research_plan_text

        context_dict['context']  = await self.generate_context(
            client, context, 
            research_plan_text
        )
        
        context_dict['context']['research_questions'] = build_string(
            await self.generate_context(
                client, research_questions, 
                research_plan_text
            )
        )
        
        context_dict['context']['thematic_areas'] = build_string(
            await self.generate_context(
                client, thematic_areas, 
                research_plan_text
            )
        )

        context_dict['agent_internals'] =  update_internals(context['context'], self.internals['agent_internals']) 
        
        with open(f'{output_folder_name}/context_dict.json', 'w') as outF:
            print("writing context")
            json.dump(context_dict, outF)
        

    async def get_context(self, client:AsyncOpenAI, research_plan_text:str, output_folder_name:str, overwrite_internals:bool=False) -> dict:
        """ Runs our initial set of document analysis on the Project folder:
            - Identifies the key information within the RFP (Research Questions, Thematic Areas)
        """
        if not os.path.exists(f"{output_folder_name}/context.json") or overwrite_internals:
            await self.create_context(client, output_folder_name, research_plan_text)
        
        print("reading context")
        return json.load(open(f'{output_folder_name}/context.json'))


    async def __call__(
        self, 
        client:AsyncOpenAI,
        output_folder_name:str,
        research_plan_text:str, 
        overwrite_context:bool=False):
        """ runs the key function of the class """
        return await self.get_context(client, research_plan_text, output_folder_name, overwrite_context)
        

router = APIRouter(tags=['context'])

def get_oai_client(client:AsyncOpenAI=Depends(get_openai_client)):
    return client


@router.get("/") 
async def generate_context(
    output_folder_name:str, 
    research_plan_text:str, 
    overwrite_context:bool=False, 
    client:AsyncOpenAI=Depends(get_oai_client)) -> dict:   
    """
    Second step in the chain is to get the contextualizing information from the RFP, 
    returns this information as a JSON and writes to the disk of the host 
    """
    return await Context(settings.AGENT_INTERNALS)(
        client=client, 
        output_folder_name=settings.PROJECT_DATA_FOLDER+output_folder_name, 
        research_plan_text=research_plan_text, 
        overwrite_context=overwrite_context, 
    )