from datetime import datetime
from decimal import Decimal

from app.models.booking import BookingStatus
from app.schemas import BaseSchema
from app.schemas.room import SRoomOut
from app.schemas.timeslot import STimeSlotOut


class SBookingBase(BaseSchema):
    user_id: int
    room_id: int
    timeslot_id: int
    status: BookingStatus
    total_price: Decimal
    paid_at: datetime | None
    canceled_at: datetime | None
    expires_at: datetime


class SBookingOut(SBookingBase):
    id: int
    room: SRoomOut


class SBookingOutAfterCreate(BaseSchema):
    id: int
    status: BookingStatus
    timeslot_id: int
    total_price: Decimal
    expires_at: datetime


class SBookingOutWithTimeslots(BaseSchema):
    booking: SBookingOut
    timeslot: STimeSlotOut


class SBookingCreate(BaseSchema):
    timeslot_id: int

class SBookingCreateFlexible(BaseSchema):
    room_id: int
    start_datetime: datetime
    end_datetime: datetime


class SBookingFilters(BaseSchema):
    room_id: int | None = None
    status: BookingStatus | None = None
