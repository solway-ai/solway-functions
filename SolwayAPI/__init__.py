from fastapi import (
    FastAPI, 
)

from SolwayAPI.api.v1.api import api_router
from SolwayAPI.api.v1.core.config import settings

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.PROJECT_VERSION,
    tags=['main']
)

app.include_router(api_router)

@app.get("/") 
async def main():     
    return {"Solway AI Engineering and Consulting API"}

@app.get("/hello") 
async def main():     
    return {"Solway AI Engineering and Consulting API"}