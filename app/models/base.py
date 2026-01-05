from datetime import datetime
from decimal import Decimal

from pydantic import ConfigDict, field_serializer
from sqlalchemy import Identity, TIMESTAMP, func
from sqlmodel import Field, SQLModel


class BaseSQLModel(SQLModel):
    __abstract__ = True
    __mapper_args__ = {"eager_defaults": True}

    id: int | None = Field(
        default=None,
        primary_key=True,
        sa_column_args=(Identity(),),
    )

    created_at: datetime = Field(
        sa_type=TIMESTAMP(timezone=True),
        nullable=False,
        sa_column_kwargs={
            "server_default": func.now()
        }
    )

    updated_at: datetime = Field(
        sa_type=TIMESTAMP(timezone=True),
        nullable=False,
        sa_column_kwargs={
            "server_default": func.now(),
            "server_onupdate": func.now()
        },
    )

    model_config = ConfigDict(from_attributes=True)

    @field_serializer("*", when_used="json")
    def _serialize_decimal(self, value):
        if isinstance(value, Decimal):
            return str(value)
        return value
