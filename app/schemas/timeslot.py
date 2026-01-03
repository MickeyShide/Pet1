from datetime import datetime, timezone
from decimal import Decimal

from pydantic import model_validator

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

class SPriceQuoteIn(BaseSchema):
    date_from: datetime
    date_to: datetime

    @model_validator(mode="after")
    def validate_dates(self):
        if self.date_to <= self.date_from:
            raise ValueError("date_to must be greater than date_from")
        return self

class SPriceQuoteOut(BaseSchema):
    price: Decimal


class STimeSlotOutWithBookingStatus(STimeSlotOut):
    has_active_booking: bool


class STimeSlotRangeOut(BaseSchema):
    id: str
    date_from: datetime
    date_to: datetime
    label: str
    hours: float


class STimeSlotDateRange(BaseSchema):
    date_from: datetime
    date_to: datetime | None = None

    @model_validator(mode="after")
    def _fill_date_to(self):
        if self.date_to is None:
            tz = self.date_from.tzinfo or timezone.utc
            self.date_to = datetime(
                self.date_from.year,
                self.date_from.month,
                self.date_from.day,
                23,
                59,
                59,
                999_999,
                tzinfo=tz,
            )
        return self


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
