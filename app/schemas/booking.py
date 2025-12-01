from datetime import datetime
from decimal import Decimal

from app.models.booking import BookingStatus
from app.schemas import BaseSchema


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

class SBookingOutAfterCreate(BaseSchema):
    id: int
    status: BookingStatus
    timeslot_id: int
    total_price: Decimal
    expires_at: datetime

class SBookingCreate(BaseSchema):
    timeslot_id: int
