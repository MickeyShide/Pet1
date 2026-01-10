from decimal import Decimal

from pydantic import model_validator

from app.models.room import RoomType, TimeSlotType
from app.schemas import BaseSchema
from app.schemas.feature import SFeatureOut
from app.schemas.image import SImageOut
from app.schemas.location import SLocationOut


class SRoomBase(BaseSchema):
    location_id: int
    name: str
    capacity: int
    description: str
    type: RoomType | None
    time_slot_type: TimeSlotType
    min_booking_duration_minutes: int
    booking_step_minutes: int
    hour_price: Decimal
    is_active: bool


class SRoomOut(SRoomBase):
    id: int
    features: list[SFeatureOut]


class SRoomOutWithLocation(SRoomOut):
    location: SLocationOut
    images: list[SImageOut]


class SRoomCreate(BaseSchema):
    name: str
    capacity: int
    description: str
    is_active: bool
    time_slot_type: TimeSlotType
    min_booking_duration_minutes: int | None = None
    booking_step_minutes: int | None = None
    hour_price: Decimal


class SRoomUpdate(BaseSchema):
    name: str | None = None
    capacity: int | None = None
    description: str | None = None
    is_active: bool | None = None
    location_id: int | None = None
    time_slot_type: TimeSlotType | None = None
    min_booking_duration_minutes: int | None = None
    booking_step_minutes: int | None = None
    hour_price: Decimal | None = None

    @model_validator(mode="after")
    def _validate_payload(self):
        payload = self.model_dump(exclude_unset=True)
        if not payload:
            raise ValueError("At least one field must be provided")
        return self
