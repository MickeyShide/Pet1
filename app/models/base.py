from datetime import datetime

from sqlalchemy import TIMESTAMP, func
from sqlmodel import Field, SQLModel


class BaseSQLModel(SQLModel):
    __abstract__ = True
    __mapper_args__ = {"eager_defaults": True}

    id: int | None = Field(default=None, primary_key=True)

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
