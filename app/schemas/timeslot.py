from datetime import datetime
from decimal import Decimal

from app.models.timeslot import TimeSlotStatus
from app.schemas import BaseSchema


class STimeSlotBase(BaseSchema):
    start_datetime: datetime
    end_datetime: datetime
    base_price: Decimal
    status: TimeSlotStatus


class STimeSlotOut(STimeSlotBase):
    id: int
    room_id: int


class STimeSlotOutWithBookingStatus(STimeSlotOut):
    has_active_booking: bool


class STimeSlotDateRange(BaseSchema):
    date_from: datetime
    date_to: datetime


class STimeSlotCreate(STimeSlotBase):
    pass


class STimeSlotUpdate(BaseSchema):
    start_datetime: datetime | None = None
    end_datetime: datetime | None = None
    base_price: Decimal | None = None
    status: TimeSlotStatus | None = None
    room_id: int | None = None

class STimeSlotFilters(BaseSchema):
    start_datetime: datetime | None = None
    end_datetime: datetime | None = None