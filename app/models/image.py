from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import Enum as SAEnum
from sqlmodel import Field, Relationship

from .base import BaseSQLModel

if TYPE_CHECKING:
    from app.models.file import File
    from app.models.location import Location
    from app.models.room import Room


class ImageType(str, Enum):
    ROOM = "ROOM"
    LOCATION = "LOCATION"


class Image(BaseSQLModel, table=True):
    __tablename__ = "images"

    image1x: str | None = None
    image2x: str | None = None
    type: ImageType = Field(
        sa_type=SAEnum(ImageType, name="pet1_imagetype")
    )
    file_id: int = Field(foreign_key="files.id")
    room_id: int | None = Field(default=None, foreign_key="rooms.id")
    location_id: int | None = Field(default=None, foreign_key="locations.id")

    file: "File" = Relationship()
    room: "Room" = Relationship(back_populates="images")
    location: "Location" = Relationship(back_populates="images")
