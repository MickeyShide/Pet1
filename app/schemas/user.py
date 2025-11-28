from pydantic import EmailStr, BaseModel

from app.models.user import UserRole


class SUserBase(BaseModel):
    first_name: str | None = None
    second_name: str | None = None
    email: EmailStr
    username: str | None = None


class SUserOut(SUserBase):
    id: int
    role: UserRole | None = None
