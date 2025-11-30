from pydantic import EmailStr

from app.schemas import BaseSchema
from app.schemas.user import SUserBase


class SRegister(SUserBase):
    password: str


class SLogin(BaseSchema):
    email: EmailStr
    password: str


class SAccessToken(BaseSchema):
    sub: str
    admin: bool


class SRefreshToken(BaseSchema):
    sub: str


class STokenOut(BaseSchema):
    access_token: str
