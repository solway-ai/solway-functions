import os

from solway_pipeline.api.v1.models.skillchain_models import Skill

from solway_pipeline.api.v1.core.skill_prompts import (
    role,
    summarization,
    figures_toc,
    keypoints,
    action_items,
    quotes
)

class Settings:

    # Domain 
    PROJECT_NAME:str = "solway.ai"
    PROJECT_VERSION:str = "1.0.0"
    OPENAPI_URL: str = "/openapi.json"
    ENV:str = os.getenv("ENV", )
    BASE_URL = os.getenv("BASE_URL", "")
    BASE_PORT = os.getenv("BASE_PORT", "")

    # API
    OPENAI_API_KEY = "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"
    VOYAGE_API_KEY = "pa-RxNy8eLNWQ1WAilqC7-0NXkNZtdLAqTVITilWMztztE"
    DBX_TOKEN = 'sl.B5oLhkSLbN9k7jpE-9sjQB7uV6zYAwJ19WYOFivCNnKWa4b9iicqECUzsLoZE3aVbdEwTy1nw18z9_svn1bo2NlkFuf-s0CSiokDkJGUSrbIDe44lxIcNWDzuFVPUWJw2QVFG-fxmPOeCkKVWue3J0I'
    APP_KEY = '8vgec6vg3xgznqf'
    APP_SECRET = 'thun7ehtkhi0j4m'


    PROJECT_DATA_FOLDER = "data/"
    PROJECT_DOCS_INDEX_NAME = "documents_index.json"
    PROJECT_DOCS_PROCESSED_NAME = "documents.json"

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