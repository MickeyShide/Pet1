from enum import Enum

from sqlmodel import Field
from sqlalchemy import Enum as SAEnum
from .base import BaseSQLModel

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
