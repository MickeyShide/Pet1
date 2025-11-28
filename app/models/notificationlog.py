from enum import Enum
from sqlalchemy import Enum as SAEnum, JSON
from sqlmodel import Field

from .base import BaseSQLModel


class NotificationLogType(str, Enum):
    BOOKING_CREATED = "BOOKING_CREATED"
    BOOKING_PAID = "BOOKING_PAID"
    BOOKING_CANCELED = "BOOKING_CANCELED"
    BOOKING_EXPIRED = "BOOKING_EXPIRED"


class NotificationLogStatus(str, Enum):
    QUEUED = "QUEUED"
    SENT = "SENT"
    FAILED = "FAILED"


class NotificationLog(BaseSQLModel, table=True):
    __tablename__ = "notificationlogs"

    user_id: int = Field(foreign_key="users.id")
    booking_id: int = Field(foreign_key="bookings.id")

    payload: str = Field(sa_type=JSON, nullable=False)

    type: NotificationLogType = Field(
        sa_type=SAEnum(NotificationLogType, name="notificationlogtype"),
        default=NotificationLogType.BOOKING_CREATED,
        nullable=False,
    )
    status: NotificationLogStatus = Field(
        sa_type=SAEnum(NotificationLogStatus, name="notificationlogstatus"),
        default=NotificationLogStatus.QUEUED,
        nullable=False,
    )

    __table_args__ = (
    )
