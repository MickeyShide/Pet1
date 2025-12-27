from decimal import Decimal
from enum import Enum
from typing import TYPE_CHECKING

from sqlmodel import Field, Relationship
from sqlalchemy import Enum as SAEnum, DECIMAL
from .base import BaseSQLModel

class RoomType(str, Enum):
    MEETING_ROOM = "MEETING_ROOM"
    COWORK_DESK = "COWORK_DESK"
    STUDIO = "STUDIO"
    SPORT = "SPORT"

class TimeSlotType(str, Enum):
    FLEXIBLE = "FLEXIBLE"  # Произвольное время
    FIXED = "FIXED"        # Конкретные таймслоты

if TYPE_CHECKING:
    from app.models.location import Location

class Room(BaseSQLModel, table=True):
    __tablename__ = "rooms"

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
    hour_price: Decimal = Field(sa_type=DECIMAL, nullable=False)
    is_active: bool
