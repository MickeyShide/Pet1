from app.schemas import BaseSchema


class SRoomBase(BaseSchema):
    name: str
    capacity: int
    description: str
    is_active: bool


class SRoomOut(SRoomBase):
    id: int
    location_id: int


class SRoomCreate(SRoomBase):
    location_id: int
    pass

class SRoomUpdate(BaseSchema):
    name: str | None = None
    capacity: int | None = None
    description: str | None = None
    is_active: bool | None = None
    location_id: int | None = None