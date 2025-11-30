from app.schemas import BaseSchema


class SLocationBase(BaseSchema):
    name: str
    address: str
    description: str


class SLocationOut(SLocationBase):
    id: int


class SLocationCreate(SLocationBase):
    pass


class SLocationUpdate(BaseSchema):
    name: str | None = None
    address: str | None = None
    description: str | None = None
