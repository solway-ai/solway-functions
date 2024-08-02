from typing import Optional

from pydantic import BaseModel

class Skill(BaseModel):
    name:str
    role:str
    instructions:str
    contiguous_on:str
    output:Optional[str]