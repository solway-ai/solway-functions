from fastapi import (
    FastAPI, 
)

# from api.v1.api import api_router
from api.v1.core.config import settings

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.PROJECT_VERSION,
    tags=['main']
)

# app.include_router(api_router)

@app.get("/") 
async def main():     
    return {"solway ai engineering"}


@app.get("/sample")
async def index():
    return {
        "info": "Try /hello/Shivani for parameterized route.",
    }


@app.get("/hello/{name}")
async def get_name(name: str):
    return {
        "name": name,
    }