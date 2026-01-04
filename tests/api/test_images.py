import types

import pytest

from app.api import deps
from app.config import settings
from app.models import Image
from app.models.image import ImageType
from app.schemas.auth import SAccessToken
from app.services.business import images as images_module


def override_token(app, *, admin: bool = False):
    async def fake_dep(jwt_token: deps.HTTPBearerDepends):
        return SAccessToken(sub="1", admin=admin)

    app.dependency_overrides[deps.get_token_data] = fake_dep


def auth_header():
    return {"Authorization": "Bearer stub"}


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
async def test__presign_requires_auth(async_client):
    response = await async_client.post(
        "/images/presign",
        json={"type": "ROOM", "mime": "image/jpeg", "ext": "jpg", "size": 123},
    )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test__presign_creates_image_and_returns_urls(async_client, db_session, monkeypatch):
    override_token(async_client.app_ref)
    s3 = StubS3()
    monkeypatch.setattr(images_module, "get_s3", lambda: s3)
    monkeypatch.setattr(images_module.uuid, "uuid4", lambda: types.SimpleNamespace(hex="abc123"))
    monkeypatch.setattr(settings, "S3_PUBLIC_BASE_URL", "http://cdn.local/")
    monkeypatch.setattr(settings, "S3_BUCKET", "uploads")

    response = await async_client.post(
        "/images/presign",
        json={"type": "ROOM", "mime": "image/jpeg", "ext": "jpg", "size": 123},
        headers=auth_header(),
    )

    async_client.app_ref.dependency_overrides.clear()
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["upload_url"] == "http://s3.local/upload/images/room/abc123.jpg"
    assert payload["public_url"] == "http://cdn.local/uploads/images/room/abc123.jpg"
    assert isinstance(payload["id"], int)

    assert len(s3.calls) == 1
    call = s3.calls[0]
    assert call["ClientMethod"] == "put_object"
    assert call["Params"]["Bucket"] == "uploads"
    assert call["Params"]["Key"] == "images/room/abc123.jpg"
    assert call["Params"]["ContentType"] == "image/jpeg"
    assert call["ExpiresIn"] == 600

    stored = await db_session.get(Image, payload["id"])
    assert stored is not None
    assert stored.image1x == "images/room/abc123.jpg"
    assert stored.image2x is None
    assert stored.type == ImageType.ROOM


@pytest.mark.asyncio
async def test__presign_invalid_payload_returns_422(async_client):
    override_token(async_client.app_ref)

    response = await async_client.post(
        "/images/presign",
        json={"type": "ROOM", "ext": "jpg", "size": 123},
        headers=auth_header(),
    )

    async_client.app_ref.dependency_overrides.clear()
    assert response.status_code == 422


@pytest.mark.asyncio
async def test__presign_invalid_type_returns_422(async_client):
    override_token(async_client.app_ref)

    response = await async_client.post(
        "/images/presign",
        json={"type": "WRONG", "mime": "image/jpeg", "ext": "jpg", "size": 123},
        headers=auth_header(),
    )

    async_client.app_ref.dependency_overrides.clear()
    assert response.status_code == 422
