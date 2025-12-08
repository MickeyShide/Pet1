from pydantic import EmailStr

from app.models.user import UserRole
from app.schemas import BaseSchema
from app.schemas.user import SUserBase, SUserOut


class SRegister(SUserBase):
    password: str


class SLogin(BaseSchema):
    email: EmailStr
    password: str


class SAccessToken(BaseSchema):
    sub: str
    admin: bool
    exp: int | None = None


class SRefreshToken(BaseSchema):
    sub: str


class SLoginOut(BaseSchema):
    access_token: str
    refresh_token: str
    user: SUserOut
