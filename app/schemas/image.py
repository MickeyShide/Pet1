from app.models.image import ImageType
from app.schemas import BaseSchema


class SImageBase(BaseSchema):
    image1x: str
    image2x: str | None = None
    type: ImageType


class SImageOut(SImageBase):
    id: int
    file_id: int
    room_id: int | None = None
    location_id: int | None = None


class SImageUploadIn(BaseSchema):
    mime: str
    ext: str
    size: int
    original_name: str | None = None


class SImagePresignOut(BaseSchema):
    id: int
    upload_url: str
    public_url: str
