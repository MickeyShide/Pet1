from typing import List, TYPE_CHECKING

from sqlmodel import Relationship

from .base import BaseSQLModel

if TYPE_CHECKING:
    from app.models.room import Room
    from app.models.feature import Feature
    from app.models.image import Image


class Location(BaseSQLModel, table=True):
    __tablename__ = "locations"

    name: str
    address: str
    description: str

    rooms: List["Room"] = Relationship(back_populates="location")
    features: List["Feature"] = Relationship(back_populates="location")
    images: List["Image"] = Relationship(back_populates="location")
