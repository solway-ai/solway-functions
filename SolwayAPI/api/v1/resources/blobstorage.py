import json 
import logging

from io import BytesIO

from typing import Optional

from azure.storage.blob import BlobServiceClient

from fastapi import (
    HTTPException,
    APIRouter, 
    Depends
)


from SolwayAPI.api.v1.core.config import settings
from SolwayAPI.api.v1.core.clients import get_blob_storage_client
from SolwayAPI.api.v1.core.utils.blobstorage_helpers import parse_files

def get_az_blob_storage_client(client:BlobServiceClient=Depends(get_blob_storage_client)):
    return client


logging.basicConfig(level=logging.INFO)

router = APIRouter(tags=['azure-blob-storage'])


@router.get("/") 
async def get_blob(blob_name:str, service_client=Depends(get_az_blob_storage_client)) -> dict:
    """ downloads, parses and returns the contents of a blob as a JSON Object """
    logging.info(f"GETTING BLOB: {settings.BLOB_STORAGE_CONTAINER_NAME}/{blob_name}")
    blob_client = service_client.get_blob_client(
        container=settings.BLOB_STORAGE_CONTAINER_NAME, 
        blob=blob_name
    )
    stream = BytesIO()
    blob_client.download_blob().readinto(stream)
    stream.seek(0)
    return parse_files({blob_name:stream.read()})



@router.post("/") 
async def create_blob(blob_name:str, content:str, overwrite:Optional[bool], service_client=Depends(get_az_blob_storage_client)) -> dict:
    """ uploads contents as a JSON to Azure Blob Storage """
    logging.info(f"CREATING BLOB: {settings.BLOB_STORAGE_CONTAINER_NAME}/{blob_name}")
    blob_client = service_client.get_blob_client(
        container=settings.BLOB_STORAGE_CONTAINER_NAME, 
        blob=blob_name
    )
    try:
        blob_client.upload_blob(json.dumps(content), content_type='application/json', overwrite=overwrite)
        return f"JSON uploaded successfully to blob: {blob_name}"

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error uploading JSON to blob: {str(e)}")


@router.get("/describe-container-contents")
async def describe_container(directory_name:Optional[str]=None, service_client=Depends(get_az_blob_storage_client)) -> dict:
    """ prints the names of the blobs in a container"""

    blob_client = service_client.get_container_client(
        container=settings.BLOB_STORAGE_CONTAINER_NAME
    )

    blob_list = blob_client.walk_blobs(name_starts_with=directory_name, delimiter='')

    files = [blob.name for blob in blob_list]

    return {
        "container_files": files
    }