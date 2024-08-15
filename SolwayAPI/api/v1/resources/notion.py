import requests

from typing import Optional

from fastapi import APIRouter

from SolwayAPI.api.v1.core.config import settings
from SolwayAPI.api.v1.core.utils.notion_helpers import (
    naive_batch,
    html_to_notion_blocks,
    markdown_to_html

)

router = APIRouter(tags=['notion'])


@router.post("/pages") 
async def create_child_notion_page(parent_id:str, title:str, subtitle:Optional[str]=None, content:Optional[str]=None):
    """ 
    Creates a child notion page of a parent Id.
    Notion API does not support programatically creating "root" pages at the workspace level.     
    The skill name is used as the subtitle, so will appear before the title in some instances
    """
    
    url = "https://api.notion.com/v1/pages"
    
    headers = {
        "Authorization": f"Bearer {settings.NOTION_API_KEY}",
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28"
    }
    
    if content:
        
        content_blocks = html_to_notion_blocks(markdown_to_html(content))
        
        # notion accepts at most 100 blocks at a time
        batches = naive_batch(content_blocks, 100)
        
        page_ids = []
        for i, batch in enumerate(batches):
            
            batch_title = f"{title}"

            if subtitle:
                batch_title = f"{subtitle} - {title}"

            if len(batches) > 1:
                batch_title = f"{subtitle} - Part {i+1} - {title}"

            payload = {
                "parent": {"type": "page_id", "page_id": parent_id},
                "properties": {
                    "title": {
                        "title": [
                            {
                                "text": {
                                    "content": batch_title
                                }
                            }
                        ] 
                    }
                },
                "children": batch
            }
            
            response = requests.post(url, json=payload, headers=headers)
            if response.status_code == 400:
                print(f"Error creating page {title}: {response.json()}")
            response.raise_for_status()
            page_ids.append(response.json()['id'])
        return page_ids
    
    else:

        payload = {
            "parent": {"type": "page_id", "page_id": parent_id},
            "properties": {
                "title": {
                    "title": [
                        {
                            "text": {
                                "content": title
                            }
                        }
                    ]
                }
            }
        }

        response = requests.post(url, json=payload, headers=headers)
        
        if response.status_code == 400:
            print(f"Error creating page {title}: {response.json()}")
        response.raise_for_status()
        
        return response.json()['id']


