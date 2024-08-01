import dropbox
import voyageai
from openai import AsyncOpenAI

from .config import settings

def get_openai_client():
    return AsyncOpenAI(
        api_key=settings.OPENAI_API_KEY
    )

def get_voyage_client():
    return voyageai.Client(api_key=settings.VOYAGE_API_KEY)


def get_dropbox_client():
    # # We will need code to refresh this Access Token
    dbx = dropbox.Dropbox(settings.DBX_TOKEN)
    return dbx