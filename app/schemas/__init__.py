from datetime import datetime, timezone

from pydantic import BaseModel, ConfigDict, field_serializer


class BaseSchema(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)

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

    def to_dict(self) -> dict:
        """
        without unset!
        """
        return self.model_dump(exclude_unset=True, exclude_none=True)
