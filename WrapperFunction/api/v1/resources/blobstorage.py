import json

from fastapi import (
    APIRouter, 
    Depends
)

# import dropbox

from api.v1.core.config import settings
from api.v1.core.clients import get_dropbox_client

from api.v1.resources.blobstorage_helpers import (
    create_folder,
    download_dropbox_folder,
    parse_files
)

router = APIRouter(tags=['dropbox'])

# def get_dbx_client(client:dropbox.Dropbox=Depends(get_dropbox_client)):
#     return client


@router.get("/download_directory") 
def get_project_folder(directory_name:str) -> dict:
    """
    writes the projects contents to the hosts disk
    """
    create_folder(directory_name)
    # files = download_dropbox_folder(dbx_client, directory_name)
    files = None
    # The raw content of each parsed document in the Dropbox folder
    processed_files = parse_files(files)

    # an index of document names
    documents_dict = {
        index:doc_name for index, doc_name in zip([i for i in range(0, len(processed_files.keys()))], list(processed_files.keys()))
    }

    with open(f"{directory_name}/{settings.PROJECT_DOCS_INDEX_NAME}.json", 'w') as outF:
        json.dump(documents_dict, outF)

    with open(f"{directory_name}/{settings.PROJECT_DOCS_PROCESSED_NAME}.json", 'w') as outF:
        json.dump(processed_files, outF)

    return {"success"}



router = APIRouter(tags=['dropbox'])
