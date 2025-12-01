from pydantic import BaseModel, ConfigDict


class BaseSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")

    @classmethod
    def from_model(cls, model_obj):
        """
        Универсальный ORM -> DTO конвертер:
        - берет только те поля, которые есть в DTO
        - игнорирует лишние поля в ORM (created_at и т.д.)
        - использует pydantic v2 model_validate
        """
        data = {}

        for field in cls.model_fields:
            if hasattr(model_obj, field):
                data[field] = getattr(model_obj, field)

        return cls(**data)
