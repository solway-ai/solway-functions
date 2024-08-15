import os

from SolwayAPI.api.v1.models.skillchain_models import Skill

from SolwayAPI.api.v1.core.skill_prompts import (
    role,
    summarization,
    figures_toc,
    keypoints,
    action_items,
    quotes,
)

class Settings:

    # Domain 
    PROJECT_NAME:str = "api.solway.ai"
    PROJECT_VERSION:str = "1.0.0"
    OPENAPI_URL: str = "/openapi.json"

    
    # API
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY") 
    VOYAGE_API_KEY = os.getenv("VOYAGE_API_KEY") 
    NOTION_API_KEY = os.getenv("NOTION_API_TOKEN") 

    BLOB_STORAGE_CONN_STRING = os.getenv("BLOB_STORAGE_STRING")
    BLOB_STORAGE_CONTAINER_NAME = os.getenv("BLOB_STORAGE_CONTAINER_NAME")


    TMP_FOLDER = "artifacts"
    CONTEXT_FILE_NAME = "context.json"
    INDEX_FILE_NAME = "index.json"


    AGENT_INTERNALS = { 
        "agent_internals": {
            "consultancy": {
                "marker": "$",
                "replacement": "",
            },
            "consultancy_task": {
                "marker": "#",
                "replacement": "",
            },
            "client": {
                "marker": "^",
                "replacement": "", 
            },
            "client_background": {
                "marker": ">",
                "replacement": "", 
            },
            "problem_statement": {
                "marker": "<",
                "replacement": "",
            },
            "research_questions": {
                "marker":"~",
                "replacement": "",
            },
            "thematic_areas": {
                "marker": "&",
                "replacement": "",
             },
        }
    }
    
    SKILLS = [
        Skill(
            name='summarization',
            role=role,
            instructions=summarization,
            contiguous_on='',
            output=''
        ),

        Skill(
            name='figures_toc',
            role=role,
            instructions=figures_toc,
            contiguous_on='',
            output=''
        ),

        Skill(
            name='action_items',
            role=role,
            instructions=action_items,
            contiguous_on='',
            output=''
        ),

        Skill(
            name='keypoints',
            role=role,
            instructions=keypoints,
            contiguous_on='',
            output=''
        ),

        Skill(
            name='quotes',
            role=role,
            instructions=quotes,
            contiguous_on='keypoints',
            output=''
        ),

    ]


    FOUNDATION_MODEL = 'gpt-4o'
    NAIVE_CHUNK_THRESHOLD = 32000


settings = Settings()