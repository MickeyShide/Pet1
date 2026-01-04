from pydantic import model_validator

from app.schemas import BaseSchema
from app.schemas.feature import SFeatureOut


class SLocationBase(BaseSchema):
    name: str
    address: str
    description: str


class SLocationOut(SLocationBase):
    id: int
    features: list[SFeatureOut]


class SLocationCreate(SLocationBase):
    pass


class SLocationUpdate(BaseSchema):
    name: str | None = None
    address: str | None = None
    description: str | None = None

    @model_validator(mode="after")
    def _validate_payload(self):
        payload = self.model_dump(exclude_unset=True)
        if not payload:
            raise ValueError("At least one field must be provided")
