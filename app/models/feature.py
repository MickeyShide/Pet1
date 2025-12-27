from enum import Enum

from sqlmodel import Field
from sqlalchemy import Enum as SAEnum, CheckConstraint
from .base import BaseSQLModel


class FeatureType(str, Enum):
    ROOM = "ROOM"
    LOCATION = "LOCATION"


class Feature(BaseSQLModel, table=True):
    __tablename__ = "features"

    name: str

    room_id: int | None = Field(default=None, foreign_key="rooms.id", nullable=True)
    location_id: int | None = Field(default=None, foreign_key="locations.id", nullable=True)

    type: FeatureType = Field(
        sa_type=SAEnum(FeatureType, name="pet1_featuretype")
    )

    __table_args__ = (
        CheckConstraint(
            """
            (
              type = 'ROOM'
              AND room_id IS NOT NULL
              AND location_id IS NULL
            )
            OR
            (
              type = 'LOCATION'
              AND location_id IS NOT NULL
              AND room_id IS NULL
            )
            """,
            name="ck_features_type_matches_fk",
        ),
    )
