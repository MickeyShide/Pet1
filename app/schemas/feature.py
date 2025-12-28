from pydantic import model_validator

from app.models.feature import FeatureType
from app.schemas import BaseSchema


class SFeatureBase(BaseSchema):
    name: str
    type: FeatureType
    room_id: int | None = None
    location_id: int | None = None

    @model_validator(mode="after")
    def _validate_target(self):
        if self.type == FeatureType.ROOM:
            if self.room_id is None or self.location_id is not None:
                raise ValueError("ROOM feature requires room_id and no location_id")
        elif self.type == FeatureType.LOCATION:
            if self.location_id is None or self.room_id is not None:
                raise ValueError("LOCATION feature requires location_id and no room_id")
        return self


class SFeatureOut(SFeatureBase):
    id: int


class SFeatureCreate(SFeatureBase):
    pass


class SFeatureUpdate(BaseSchema):
    name: str | None = None
    type: FeatureType | None = None
    room_id: int | None = None
    location_id: int | None = None

    @model_validator(mode="after")
    def _validate_target(self):
        if self.room_id is not None and self.location_id is not None:
            raise ValueError("feature cannot target both room and location")
        if self.type == FeatureType.ROOM and self.location_id is not None:
            raise ValueError("ROOM feature cannot include location_id")
        if self.type == FeatureType.LOCATION and self.room_id is not None:
            raise ValueError("LOCATION feature cannot include room_id")
        return self
