from datetime import datetime
from enum import Enum

from sqlalchemy import Enum as SAEnum, CheckConstraint, UniqueConstraint, text
from sqlalchemy import TIMESTAMP, DECIMAL
from sqlalchemy.dialects.postgresql import ExcludeConstraint
from sqlmodel import Field

from .base import BaseSQLModel


class TimeSlotStatus(str, Enum):
    AVAILABLE = "AVAILABLE"
    BLOCKED = "BLOCKED"


class TimeSlot(BaseSQLModel, table=True):
    __tablename__ = "timeslots"

    room_id: int = Field(foreign_key="rooms.id", nullable=False)

    start_datetime: datetime = Field(sa_type=TIMESTAMP(timezone=True), nullable=False)
    end_datetime: datetime = Field(sa_type=TIMESTAMP(timezone=True), nullable=False)

    base_price: float = Field(sa_type=DECIMAL, nullable=False)

    status: TimeSlotStatus = Field(
        sa_type=SAEnum(TimeSlotStatus, name="timeslotstatus"),
        default=TimeSlotStatus.AVAILABLE,
        nullable=False,
    )

    __table_args__ = (

        # start < end
        CheckConstraint(
            "start_datetime < end_datetime",
            name="ck_timeslot_start_before_end",
        ),

        # unique start-end pair
        UniqueConstraint(
            "room_id",
            "start_datetime",
            "end_datetime",
            name="uq_timeslot_unique_range",
        ),

        # overlapping time intervals
        ExcludeConstraint(
            ("room_id", "="),
            (
                text("tstzrange(start_datetime, end_datetime, '[]')"),
                "&&",
            ),
            name="timeslot_no_overlap_per_room",
            using="gist",
        ),
    )
