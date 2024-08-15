# import dropbox

import voyageai
from openai import AsyncOpenAI

from azure.storage.blob import BlobServiceClient

from .config import settings

def get_openai_client():
    return AsyncOpenAI(
        api_key=settings.OPENAI_API_KEY
    )

def get_voyage_client():
    return voyageai.Client(api_key=settings.VOYAGE_API_KEY)


def get_blob_storage_client():
    return BlobServiceClient.from_connection_string(settings.BLOB_STORAGE_CONN_STRING)


# def get_dropbox_client():
#     # # We will need code to refresh this Access Token
#     dbx = dropbox.Dropbox(settings.DBX_TOKEN)
#     return dbx