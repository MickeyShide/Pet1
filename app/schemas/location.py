from pydantic import BaseModel


class SLocationBase(BaseModel):
    name: str
    address: str
    description: str

class SLocationOut(SLocationBase):
    id: int

class SLocationCreate(SLocationBase):
    pass