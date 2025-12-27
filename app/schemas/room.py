from decimal import Decimal

from app.models.room import RoomType, TimeSlotType
from app.schemas import BaseSchema
from app.schemas.location import SLocationOut


class SRoomBase(BaseSchema):
    location_id: int
    name: str
    capacity: int
    description: str
    type: RoomType | None
    image_id: int | None
    time_slot_type: TimeSlotType
    hour_price: Decimal
    is_active: bool



class SRoomOut(SRoomBase):
    id: int

class SRoomOutWithLocation(SRoomOut):
    location: SLocationOut


class SRoomCreate(BaseSchema):
    name: str
    capacity: int
    description: str
    is_active: bool
    time_slot_type: TimeSlotType
    hour_price: Decimal


class SRoomUpdate(BaseSchema):
    name: str | None = None
    capacity: int | None = None
    description: str | None = None
    is_active: bool | None = None
    location_id: int | None = None
    time_slot_type: TimeSlotType | None = None
    hour_price: Decimal | None = None
