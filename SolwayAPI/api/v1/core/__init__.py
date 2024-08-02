from fastapi import APIRouter

from SolwayAPI.api.v1.resources import(
    context,
    skillchain,
    blobstorage
)

api_router = APIRouter(prefix="/v1")

api_router.include_router(
    context.router, 
    prefix="/context", 
    tags=["context"]
)

api_router.include_router(
    skillchain.router, 
    prefix="/skills", 
    tags=["skillchain"]
)

api_router.include_router(
    blobstorage.router, 
    prefix="/files", 
    tags=["blobstorage"]
)
