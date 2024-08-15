
import asyncio 

import logging 

from typing import List, Optional

from fastapi import (
    APIRouter, 
    Depends
)

from pathlib import Path

from openai import AsyncOpenAI
from voyageai import Client as VoyageClient
from azure.storage.blob import BlobServiceClient

from SolwayAPI.api.v1.core.utils.blobstorage_helpers import get_file_name

from .artifacts import (
    get_voyage_ai_client,
    create_index_record,
    generate_context,
    
)

from .skillchain import (
    get_oai_client,
    generate_skills
)

from .rag import (
    retrieval_aug_gen
)

from .notion import create_child_notion_page

from .blobstorage import (
    get_az_blob_storage_client,
    describe_container,
)


logging.basicConfig(level=logging.INFO)

router = APIRouter(tags=['pipeline'])


async def process_file(oai_client:AsyncOpenAI, skills:list, filename:str, project_folder_name:str, project_notion_page_id:str,  overwrite:bool, blob_client:BlobServiceClient):
    # create a link page on the project page
    file_page_id = await create_child_notion_page(project_notion_page_id, Path(get_file_name(filename)).stem)

    await generate_skills(
        oai_client=oai_client,
        skills=skills,
        filename=filename,
        project_folder_name=project_folder_name,
        notion_page_id=file_page_id,
        overwrite=overwrite,
        blob_client=blob_client
    )


def filter_files_in_directory(blob_list, project_folder_name):
    """
    filters file based on specific directory
    """
    # Normalize the project folder name to ensure it ends with a '/'
    if not project_folder_name.endswith('/'):
        project_folder_name += '/'
    
    # List to store the filtered files
    filtered_files = []

    for blob_name in blob_list:
        # Check if the blob is directly under the project folder (and not in subdirectories)
        if blob_name.startswith(project_folder_name) and '/' not in blob_name[len(project_folder_name):]:
            filtered_files.append(blob_name)
    
    return filtered_files



@router.post("/") 
async def run_pipeline(    
    project_folder_name:str,
    research_plan_name:str,
    project_notion_page_id:str,
    skills:List[str],
    overwrite:Optional[bool]=False,
    oai_client:AsyncOpenAI=Depends(get_oai_client), 
    vo_client:VoyageClient=Depends(get_voyage_ai_client), 
    blob_client:BlobServiceClient=Depends(get_az_blob_storage_client)) -> dict:
    """
    project_notion_page_id: 5fafa95792794aa59be594105ecb5c73 \n

    project_folder_name: city_of_kelowna/sub_project_1 \n

    research_plan_name: city_of_kelowna/sub_project_1/20240524_KelownaClimateDev_Research Plan vEPR.pdf \n

    skills: ["summarization", "keypoints", "quotes"]
    """

    file_names = await describe_container(project_folder_name, service_client=blob_client)
    logging.info(f"Described File names: {file_names['container_files']}")
    file_names = file_names["container_files"]
    file_names = filter_files_in_directory(file_names, project_folder_name)
    file_names = [name for name in file_names if name != research_plan_name]

    logging.info(f"Filtered Filename: {file_names}")

    context = await generate_context(
        project_folder_name=project_folder_name, 
        proposal_file_name=research_plan_name,
        overwrite=overwrite,
        oai_client=oai_client,
        blob_client=blob_client
    )

    logging.info("got context")

    for filename in file_names:
        await create_index_record(project_folder_name=project_folder_name, file_name=filename, vo_client=vo_client, blob_client=blob_client)

    logging.info("created index")

    logging.info("GENERATING SKILLS")

    await asyncio.gather(*[process_file(oai_client, skills, filename, project_folder_name, project_notion_page_id, overwrite, blob_client) for filename in file_names])

    logging.info("generated skills")

    logging.info("GENERATING RESEARCH QUESTIONS")
    questions = context['context']['research_questions'].split("\n")
    questions = [q.strip('- ') for q in questions[1:] if q]

    await retrieval_aug_gen(
        project_folder_name=project_folder_name,
        top_n=30,
        notion_page_id=project_notion_page_id,
        overwrite=overwrite,
        oai_client=oai_client,
        vo_client=vo_client,
        blob_client=blob_client
    )

    return {
        "pipe_completion_state": True
    }
