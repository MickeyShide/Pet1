from enum import Enum

from sqlalchemy import UniqueConstraint
from sqlalchemy import Enum as SAEnum
from sqlmodel import Field

from .base import BaseSQLModel


class PaymentStatus(str, Enum):
    CREATED = "CREATED"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"


class Payment(BaseSQLModel, table=True):
    __tablename__ = "payments"

    booking_id: int = Field(foreign_key="bookings.id", nullable=False, unique=True)
    external_id: str  # fake ID from "payment service"

    status: PaymentStatus = Field(
        sa_type=SAEnum(PaymentStatus, name="paymentstatus"),
        default=PaymentStatus.CREATED,
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint(
            "booking_id",
            name="uq_payment_booking_id",
        ),
    )
