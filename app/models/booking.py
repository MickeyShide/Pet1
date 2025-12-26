from datetime import datetime
from decimal import Decimal
from enum import Enum

from sqlalchemy import Enum as SAEnum, Index, text
from sqlalchemy import TIMESTAMP, DECIMAL
from sqlmodel import Field

from .base import BaseSQLModel


class BookingStatus(str, Enum):
    PENDING_PAYMENTS = "PENDING_PAYMENTS"
    PAID = "PAID"
    CANCELED = "CANCELED"
    EXPIRED = "EXPIRED"


class Booking(BaseSQLModel, table=True):
    __tablename__ = "bookings"

    user_id: int = Field(foreign_key="users.id", nullable=False)
    room_id: int = Field(foreign_key="rooms.id", nullable=False)
    timeslot_id: int = Field(foreign_key="timeslots.id", nullable=False)

    status: BookingStatus = Field(
        sa_type=SAEnum(BookingStatus, name="bookingstatus"),
        default=BookingStatus.PENDING_PAYMENTS,
        nullable=False,
    )
    total_price: Decimal = Field(sa_type=DECIMAL, nullable=False)

    paid_at: datetime | None = Field(sa_type=TIMESTAMP(timezone=True), nullable=True)
    canceled_at: datetime | None = Field(sa_type=TIMESTAMP(timezone=True), nullable=True)
    expires_at: datetime = Field(sa_type=TIMESTAMP(timezone=True), nullable=False)

    __table_args__ = (
        Index(
            "uq_bookings_timeslot_active",
            "timeslot_id",
            unique=True,
            postgresql_where=text(
                "status IN ('PENDING_PAYMENTS', 'PAID')"
            ),
        ),
    )
