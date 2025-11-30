from pydantic import EmailStr

from app.models.user import UserRole
from app.schemas import BaseSchema


class SUserBase(BaseSchema):
    first_name: str | None = None
    second_name: str | None = None
    email: EmailStr
    username: str | None = None


class SUserOut(SUserBase):
    id: int
    role: UserRole | None = None
