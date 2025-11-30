from pydantic import BaseModel, EmailStr

from app.schemas.user import SUserBase


class SRegister(SUserBase):
    password: str

class SLogin(BaseModel):
    email: EmailStr
    password: str

class SAccessToken(BaseModel):
    sub: str
    admin: bool

class SRefreshToken(BaseModel):
    sub: str


class STokenOut(BaseModel):
    access_token: str