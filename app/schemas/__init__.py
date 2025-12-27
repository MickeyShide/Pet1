from pydantic import BaseModel, ConfigDict


class BaseSchema(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)

    @classmethod
    def from_model(cls, model_obj):
        """
        Универсальный ORM -> DTO конвертер:
        - берет только те поля, которые есть в DTO
        - игнорирует лишние поля в ORM (created_at и т.д.)
        - использует pydantic v2 model_validate
        """
        return cls.model_validate(model_obj)
