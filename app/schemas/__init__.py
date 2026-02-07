from datetime import datetime, timezone
from typing import ClassVar

import pydantic.fields
from pydantic import BaseModel, ConfigDict, field_serializer
from pydantic.fields import PydanticUndefined


class BaseSchema(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)

    UNSET: ClassVar = PydanticUndefined

    @field_serializer("*", when_used="json")
    def _serialize_datetime(self, value):
        if isinstance(value, datetime):
            if value.tzinfo is None:
                value = value.replace(tzinfo=timezone.utc)
            return value.isoformat()
        return value

    @classmethod
    def from_model(cls, model_obj):
        """
        Универсальный ORM -> DTO конвертер:
        - берет только те поля, которые есть в DTO
        - игнорирует лишние поля в ORM (created_at и т.д.)
        - использует pydantic v2 model_validate
        """
        return cls.model_validate(model_obj)

    @classmethod
    def unset(cls):
        return cls.UNSET

    def to_dict(self) -> dict:
        """
        without unset!
        """
        payload = self.model_dump(exclude_unset=True)
        return {key: value for key, value in payload.items() if value is not self.UNSET}
