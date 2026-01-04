from app.models.image import ImageType
from app.schemas import BaseSchema


class SImageBase(BaseSchema):
    image1x: str
    image2x: str | None = None
    type: ImageType


class SImageOut(SImageBase):
    id: int


class SImagePresignIn(BaseSchema):
    type: ImageType
    mime: str
    ext: str
    size: int


class SImagePresignOut(BaseSchema):
    id: int
    upload_url: str
    public_url: str
