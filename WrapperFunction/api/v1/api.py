from fastapi import APIRouter

from solway_pipeline.api.v1.resources import(
    context,
    skillchain,
    dropbox
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
    dropbox.router, 
    prefix="/files", 
    tags=["dropbox"]
)
