from datetime import datetime
from decimal import Decimal
from enum import Enum

from sqlalchemy import Enum as SAEnum, CheckConstraint, Index, text
from sqlalchemy import TIMESTAMP, DECIMAL
from sqlalchemy.dialects.postgresql import ExcludeConstraint
from sqlmodel import Field

from .base import BaseSQLModel


class TimeSlotStatus(str, Enum):
    AVAILABLE = "AVAILABLE"
    BLOCKED = "BLOCKED"
    CANCELED = "CANCELED"


class TimeSlot(BaseSQLModel, table=True):
    __tablename__ = "timeslots"

    room_id: int = Field(foreign_key="rooms.id", nullable=False)

    start_datetime: datetime = Field(sa_type=TIMESTAMP(timezone=True), nullable=False)
    end_datetime: datetime = Field(sa_type=TIMESTAMP(timezone=True), nullable=False)

    base_price: Decimal = Field(sa_type=DECIMAL, nullable=False)

    status: TimeSlotStatus = Field(
        sa_type=SAEnum(TimeSlotStatus, name="timeslotstatus"),
        default=TimeSlotStatus.AVAILABLE,
        nullable=False,
        sa_column_kwargs={"server_default": text("'AVAILABLE'")},
    )

    __table_args__ = (
        CheckConstraint("start_datetime < end_datetime", name="ck_timeslot_start_before_end"),

        Index(
            "uq_timeslot_unique_range_active",
            "room_id",
            "start_datetime",
            "end_datetime",
            unique=True,
            postgresql_where=text("status != 'CANCELED'"),
            sqlite_where=text("status != 'CANCELED'"),
        ),

        ExcludeConstraint(
            ("room_id", "="),
            (text("tstzrange(start_datetime, end_datetime, '[)')"), "&&"),
            name="timeslot_no_overlap_available_per_room",
            using="gist",
            where=text("status != 'CANCELED'"),
        ),
    )
