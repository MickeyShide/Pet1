from sqlmodel import Field

from .base import BaseSQLModel


class Room(BaseSQLModel, table=True):
    __tablename__ = "rooms"

    location_id: int = Field(foreign_key="locations.id", nullable=False)

    name: str
    capacity: int
    description: str
    is_active: bool