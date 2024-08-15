from fastapi import APIRouter

from SolwayAPI.api.v1.resources import(
    pipe,
    artifacts,
    skillchain,
    blobstorage,
    notion,
    rag
)

api_router = APIRouter(prefix="/v1")


api_router.include_router(
    pipe.router, 
    prefix="/pipeline", 
    tags=["pipeline"]
)


api_router.include_router(
    artifacts.router, 
    prefix="/artifacts", 
    tags=["artifacts"]
)


api_router.include_router(
    rag.router, 
    prefix="/retrieval", 
    tags=["retrieval"]
)


api_router.include_router(
    skillchain.router, 
    prefix="/skills", 
    tags=["skillchain"]
)

api_router.include_router(
    blobstorage.router, 
    prefix="/blobs", 
    tags=["azure-blob-storage"]
)

api_router.include_router(
    notion.router, 
    prefix="/notion", 
    tags=["notion"]
)