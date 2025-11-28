from enum import Enum

from pydantic import EmailStr
from sqlalchemy import Enum as SAEnum
from sqlmodel import Field

from .base import BaseSQLModel


class UserRole(str, Enum):
    USER = "USER"
    ADMIN = "ADMIN"


class User(BaseSQLModel, table=True):
    __tablename__ = "users"

    first_name: str | None = Field(default=None, nullable=True)
    second_name: str | None = Field(default=None, nullable=True)

    email: EmailStr = Field(index=True, nullable=False, unique=True)
    username: str | None = Field(default=None, index=True, nullable=True, unique=True)
    hashed_password: str

    role: UserRole | None = Field(
        sa_type=SAEnum(UserRole, name="userrole"),
        default=UserRole.USER,
        nullable=False,
    )
