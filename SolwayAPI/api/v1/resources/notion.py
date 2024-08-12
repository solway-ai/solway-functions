import json
import requests

from typing import Union

from fastapi import APIRouter

from SolwayAPI.api.v1.core.config import settings
from SolwayAPI.api.v1.resources.notion_helpers import (
    naive_batch,
    html_to_notion_blocks,
    markdown_to_html

)

router = APIRouter(tags=['notion'])


@router.post("/pages") 
def create_notion_page(parent_id:str, name:str, title=Union[str, None], content=Union[str, None]):
    """ 
    Creates a notion page 
    Solway Root Project ID: "8b7ae4a9fcf946958cc9ec49578c020a"

    """
    
    url = "https://api.notion.com/v1/pages"
    
    headers = {
        "Authorization": f"Bearer {settings.NOTION_API_TOKEN}",
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28"
    }
    
    if content:
        
        content_blocks = html_to_notion_blocks(markdown_to_html(content))
        
        # notion accepts at most 100 blocks at a time
        batches = naive_batch(content_blocks, 100)
        
        page_ids = []
        for i, batch in enumerate(batches):
            
            batch_title = f"{name}"

            if title:
                batch_title = f"{title} - {name}"

            if len(batches) > 1:
                batch_title = f"{title} - Part {i+1} - {name}"

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
                                "content": name
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




    # for rq, answer in data_list.items():
    #     source_document_name = rq
    #     source_document_page_id = create_notion_page(parent_id=main_page_id, name=source_document_name, content=answer)


    # # Iterate over each JSON object in the list and create pages
    # for data in data_list:
    #     # Create the source document page
    #     source_document_name = data['source_document']
    #     print(f"Creating {source_document_name} Page...")
    #     source_document_page_id = create_notion_page(parent_id=main_page_id, name=source_document_name)
    #     print(f"Created Page Id: {source_document_page_id}\n\n")

    #     print(f"Adding {source_document_name} Content...")
    #     # Create sub-pages for each key in the JSON (excluding 'source_document')
    #     for key in ['summarization', 'keypoints', 'action_items', 'quotes', 'figures_toc']:
    #         #print(f"Payload: {data[key]}")
    #         if key != 'textIN':
    #             create_notion_page(parent_id=source_document_page_id, name=source_document_name, title=key, content=data[key])
    #         else:
    #             create_notion_page(parent_id=source_document_page_id, name=source_document_name, title=key, content=data[key], is_raw_text=True)
    #         print(f"Added: {key} to {source_document_name}")
    #     print("")



    # Folder name and JSON file
    # root_page = "Sub-project #1 (Existing Practice Review)"

    # # product_df.to_json(f"{FOLDER_NAME}_product.json", orient="records")
    # block_content = f"{FOLDER_NAME}/skills/research_questions/research_questions.json"

    # # Load the JSON data
    # with open(block_content, 'r') as file:
    #     data_list = json.load(file)

    # main_page_id = create_notion_page(SOLWAY_PAGE_ID, f"Existing Practice Review Dev")
    # return None
