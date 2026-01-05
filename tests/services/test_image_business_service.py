import types

import pytest

from app.config import settings
from app.models import Image
from app.models.image import ImageType
from app.schemas.image import SImagePresignIn
from app.services.business import images as images_module
from app.services.business.images import ImageBusinessService


class StubS3:
    def __init__(self):
        self.calls = []

    def generate_presigned_url(self, ClientMethod, Params, ExpiresIn):
        self.calls.append(
            {
                "ClientMethod": ClientMethod,
                "Params": Params,
                "ExpiresIn": ExpiresIn,
            }
        )
        return f"http://s3.local/upload/{Params['Key']}"


@pytest.mark.asyncio
async def test__image_business_presign_creates_image(db_session, monkeypatch):
    s3 = StubS3()
    monkeypatch.setattr(images_module, "get_s3", lambda: s3)
    monkeypatch.setattr(images_module.uuid, "uuid4", lambda: types.SimpleNamespace(hex="abc123"))
    monkeypatch.setattr(settings, "S3_PUBLIC_BASE_URL", "http://cdn.local/")
    monkeypatch.setattr(settings, "S3_BUCKET", "uploads")

    payload = SImagePresignIn(type=ImageType.ROOM, mime="image/png", ext="png", size=321)
    result = await ImageBusinessService().presign(payload)

    assert result.upload_url == "http://s3.local/upload/images/room/abc123.png"
    assert result.public_url == "http://cdn.local/uploads/images/room/abc123.png"
    assert isinstance(result.id, int)

    assert len(s3.calls) == 1
    call = s3.calls[0]
    assert call["ClientMethod"] == "put_object"
    assert call["Params"]["Bucket"] == "uploads"
    assert call["Params"]["Key"] == "images/room/abc123.png"
    assert call["Params"]["ContentType"] == "image/png"
    assert call["ExpiresIn"] == 600

    stored = await db_session.get(Image, result.id)
    assert stored is not None
    assert stored.image1x == "images/room/abc123.png"
    assert stored.image2x is None
    assert stored.type == ImageType.ROOM
