from decimal import Decimal
from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import Enum as SAEnum, DECIMAL, CheckConstraint, text
from sqlmodel import Field, Relationship

from .base import BaseSQLModel


class RoomType(str, Enum):
    MEETING_ROOM = "MEETING_ROOM"
    COWORK_DESK = "COWORK_DESK"
    STUDIO = "STUDIO"
    SPORT = "SPORT"


class TimeSlotType(str, Enum):
    FLEXIBLE = "FLEXIBLE"  # Произвольное время
    FIXED = "FIXED"  # Конкретные таймслоты


if TYPE_CHECKING:
    from app.models.location import Location
    from app.models.feature import Feature
    from app.models.booking import Booking


class Room(BaseSQLModel, table=True):
    __tablename__ = "rooms"
    __table_args__ = (
        CheckConstraint(
            "min_booking_duration_minutes > 0",
            name="ck_rooms_min_booking_duration_minutes_positive",
        ),
        CheckConstraint(
            "booking_step_minutes > 0",
            name="ck_rooms_booking_step_minutes_positive",
        ),
        CheckConstraint(
            "booking_step_minutes <= min_booking_duration_minutes",
            name="ck_rooms_booking_step_lte_min_duration",
        ),
    )

    location_id: int = Field(foreign_key="locations.id", nullable=False)
    location: "Location" = Relationship(back_populates="rooms")

    name: str
    capacity: int
    description: str
    type: RoomType | None = Field(
        default=None,
        sa_type=SAEnum(RoomType, name="pet1_roomtype"),
    )

    image_id: int | None = Field(default=None, foreign_key="images.id", nullable=True)

    time_slot_type: TimeSlotType = Field(
        sa_type=SAEnum(TimeSlotType, name="pet1_timeslottype"), default=TimeSlotType.FLEXIBLE
    )

    min_booking_duration_minutes: int = Field(
        default=60, nullable=False, sa_column_kwargs={"server_default": text("60")}
    )
    booking_step_minutes: int = Field(
        default=60, nullable=False, sa_column_kwargs={"server_default": text("60")}
    )

    hour_price: Decimal = Field(sa_type=DECIMAL, nullable=False)
    is_active: bool

    features: list["Feature"] = Relationship(back_populates="room")
    bookings: list["Booking"] = Relationship(back_populates="room")
