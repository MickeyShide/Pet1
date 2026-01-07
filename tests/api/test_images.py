import pytest
from sqlalchemy import select

from app.api import deps
from app.config import settings
from app.models import File, Image
from app.models.file import FileStatus
from app.models.image import ImageType
from app.schemas.auth import SAccessToken
from app.services.file import FileService
from app.utils.file_utils import sanitize_filename
from tests.fixtures.factories import create_location, create_room, create_user


def override_admin_token(app, *, user_id: int):
    async def fake_dep(jwt_token: deps.HTTPBearerDepends):
        return SAccessToken(sub=str(user_id), admin=True)

    app.dependency_overrides[deps.get_token_data] = fake_dep


def override_user_token(app, *, user_id: int):
    async def fake_dep(jwt_token: deps.HTTPBearerDepends):
        return SAccessToken(sub=str(user_id), admin=False)

    app.dependency_overrides[deps.get_token_data] = fake_dep


def auth_header():
    return {"Authorization": "Bearer stub"}


@pytest.mark.asyncio
async def test__upload_room_image_requires_auth(async_client):
    response = await async_client.post(
        "/rooms/1/upload_image",
        json={"mime": "image/png", "ext": "png", "size": 123},
    )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test__upload_room_image_requires_admin(async_client, db_session, faker):
    user = await create_user(db_session, faker)
    override_user_token(async_client.app_ref, user_id=user.id)

    response = await async_client.post(
        "/rooms/1/upload_image",
        json={"mime": "image/png", "ext": "png", "size": 123},
        headers=auth_header(),
    )

    async_client.app_ref.dependency_overrides.clear()
    assert response.status_code == 403


@pytest.mark.asyncio
async def test__upload_location_image_requires_auth(async_client):
    response = await async_client.post(
        "/locations/1/upload_image",
        json={"mime": "image/png", "ext": "png", "size": 123},
    )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test__upload_location_image_requires_admin(async_client, db_session, faker):
    user = await create_user(db_session, faker)
    override_user_token(async_client.app_ref, user_id=user.id)

    response = await async_client.post(
        "/locations/1/upload_image",
        json={"mime": "image/png", "ext": "png", "size": 123},
        headers=auth_header(),
    )

    async_client.app_ref.dependency_overrides.clear()
    assert response.status_code == 403


@pytest.mark.asyncio
async def test__upload_room_image_returns_presign(async_client, db_session, faker, monkeypatch):
    user = await create_user(db_session, faker)
    location = await create_location(db_session, faker)
    room = await create_room(db_session, faker, location=location)
    await db_session.commit()
    override_admin_token(async_client.app_ref, user_id=user.id)

    monkeypatch.setattr(settings, "S3_PUBLIC_BASE_URL", "http://cdn.local/")
    monkeypatch.setattr(settings, "S3_PUBLIC_BUCKET", "public-uploads")
    monkeypatch.setattr(settings, "FILES_ALLOWED_CONTENT_TYPES", "image/png,image/jpeg")

    async def fake_presign_upload_put(self, bucket, key, content_type, expires):
        return f"http://s3.local/upload/{key}"

    monkeypatch.setattr(FileService, "presign_upload_put", fake_presign_upload_put)

    response = await async_client.post(
        f"/rooms/{room.id}/upload_image",
        json={"mime": "image/png", "ext": "png", "size": 123, "original_name": "room.png"},
        headers=auth_header(),
    )

    async_client.app_ref.dependency_overrides.clear()
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["upload_url"].startswith("http://s3.local/upload/images/rooms/")
    assert payload["public_url"].startswith("http://cdn.local/public-uploads/images/rooms/")

    stored_image = await db_session.get(Image, payload["id"])
    assert stored_image is not None
    assert stored_image.room_id == room.id
    assert stored_image.type == ImageType.ROOM

    stored_file = await db_session.get(File, stored_image.file_id)
    assert stored_file is not None
    assert stored_file.public_url == payload["public_url"]
    assert stored_file.is_public is True
    assert stored_file.status == FileStatus.PENDING
    assert stored_file.bucket == "public-uploads"


@pytest.mark.asyncio
async def test__upload_room_image_not_found(async_client, db_session, faker):
    user = await create_user(db_session, faker)
    override_admin_token(async_client.app_ref, user_id=user.id)

    response = await async_client.post(
        "/rooms/999999/upload_image",
        json={"mime": "image/png", "ext": "png", "size": 123},
        headers=auth_header(),
    )

    async_client.app_ref.dependency_overrides.clear()
    assert response.status_code == 404


@pytest.mark.asyncio
async def test__upload_room_image_invalid_payload_missing_fields(async_client, db_session, faker):
    user = await create_user(db_session, faker)
    override_admin_token(async_client.app_ref, user_id=user.id)

    response = await async_client.post(
        "/rooms/1/upload_image",
        json={"mime": "image/png"},
        headers=auth_header(),
    )

    async_client.app_ref.dependency_overrides.clear()
    assert response.status_code == 422


@pytest.mark.asyncio
async def test__upload_room_image_invalid_payload_types(async_client, db_session, faker):
    user = await create_user(db_session, faker)
    override_admin_token(async_client.app_ref, user_id=user.id)

    response = await async_client.post(
        "/rooms/1/upload_image",
        json={"mime": "image/png", "ext": "png", "size": "bad"},
        headers=auth_header(),
    )

    async_client.app_ref.dependency_overrides.clear()
    assert response.status_code == 422


@pytest.mark.asyncio
async def test__upload_room_image_invalid_content_type(async_client, db_session, faker, monkeypatch):
    user = await create_user(db_session, faker)
    location = await create_location(db_session, faker)
    room = await create_room(db_session, faker, location=location)
    await db_session.commit()
    override_admin_token(async_client.app_ref, user_id=user.id)

    monkeypatch.setattr(settings, "FILES_ALLOWED_CONTENT_TYPES", "image/png")

    response = await async_client.post(
        f"/rooms/{room.id}/upload_image",
        json={"mime": "image/jpeg", "ext": "jpg", "size": 123},
        headers=auth_header(),
    )

    async_client.app_ref.dependency_overrides.clear()
    assert response.status_code == 415


@pytest.mark.asyncio
async def test__upload_room_image_invalid_size(async_client, db_session, faker, monkeypatch):
    user = await create_user(db_session, faker)
    location = await create_location(db_session, faker)
    room = await create_room(db_session, faker, location=location)
    await db_session.commit()
    override_admin_token(async_client.app_ref, user_id=user.id)

    monkeypatch.setattr(settings, "S3_MAX_UPLOAD_BYTES_PRESIGNED", 10)
    monkeypatch.setattr(settings, "FILES_ALLOWED_CONTENT_TYPES", "image/png")

    response = await async_client.post(
        f"/rooms/{room.id}/upload_image",
        json={"mime": "image/png", "ext": "png", "size": 11},
        headers=auth_header(),
    )

    async_client.app_ref.dependency_overrides.clear()
    assert response.status_code == 413


@pytest.mark.asyncio
async def test__upload_room_image_invalid_size_zero(async_client, db_session, faker, monkeypatch):
    user = await create_user(db_session, faker)
    location = await create_location(db_session, faker)
    room = await create_room(db_session, faker, location=location)
    await db_session.commit()
    override_admin_token(async_client.app_ref, user_id=user.id)

    monkeypatch.setattr(settings, "FILES_ALLOWED_CONTENT_TYPES", "image/png")

    response = await async_client.post(
        f"/rooms/{room.id}/upload_image",
        json={"mime": "image/png", "ext": "png", "size": 0},
        headers=auth_header(),
    )

    async_client.app_ref.dependency_overrides.clear()
    assert response.status_code == 422


@pytest.mark.asyncio
async def test__upload_room_image_negative_size(async_client, db_session, faker, monkeypatch):
    user = await create_user(db_session, faker)
    location = await create_location(db_session, faker)
    room = await create_room(db_session, faker, location=location)
    await db_session.commit()
    override_admin_token(async_client.app_ref, user_id=user.id)

    monkeypatch.setattr(settings, "FILES_ALLOWED_CONTENT_TYPES", "image/png")

    response = await async_client.post(
        f"/rooms/{room.id}/upload_image",
        json={"mime": "image/png", "ext": "png", "size": -1},
        headers=auth_header(),
    )

    async_client.app_ref.dependency_overrides.clear()
    assert response.status_code == 422


@pytest.mark.asyncio
async def test__upload_room_image_sanitizes_original_name(async_client, db_session, faker, monkeypatch):
    user = await create_user(db_session, faker)
    location = await create_location(db_session, faker)
    room = await create_room(db_session, faker, location=location)
    await db_session.commit()
    override_admin_token(async_client.app_ref, user_id=user.id)

    monkeypatch.setattr(settings, "S3_PUBLIC_BASE_URL", "http://cdn.local/")
    monkeypatch.setattr(settings, "S3_PUBLIC_BUCKET", "public-uploads")
    monkeypatch.setattr(settings, "FILES_ALLOWED_CONTENT_TYPES", "image/png,image/jpeg")

    async def fake_presign_upload_put(self, bucket, key, content_type, expires):
        return f"http://s3.local/upload/{key}"

    monkeypatch.setattr(FileService, "presign_upload_put", fake_presign_upload_put)

    original_name = "  ../bad/name.png  "
    response = await async_client.post(
        f"/rooms/{room.id}/upload_image",
        json={
            "mime": "image/png",
            "ext": "png",
            "size": 123,
            "original_name": original_name,
        },
        headers=auth_header(),
    )

    async_client.app_ref.dependency_overrides.clear()
    assert response.status_code == 200

    stored_image = await db_session.get(Image, response.json()["id"])
    stored_file = await db_session.get(File, stored_image.file_id)
    assert stored_file.original_name == sanitize_filename(original_name)


@pytest.mark.asyncio
async def test__upload_room_image_rejects_null_byte_name(async_client, db_session, faker, monkeypatch):
    user = await create_user(db_session, faker)
    location = await create_location(db_session, faker)
    room = await create_room(db_session, faker, location=location)
    await db_session.commit()
    override_admin_token(async_client.app_ref, user_id=user.id)

    monkeypatch.setattr(settings, "FILES_ALLOWED_CONTENT_TYPES", "image/png")

    response = await async_client.post(
        f"/rooms/{room.id}/upload_image",
        json={
            "mime": "image/png",
            "ext": "png",
            "size": 123,
            "original_name": "bad\x00name.png",
        },
        headers=auth_header(),
    )

    async_client.app_ref.dependency_overrides.clear()
    assert response.status_code == 422


@pytest.mark.asyncio
async def test__upload_room_image_allows_multiple(async_client, db_session, faker, monkeypatch):
    user = await create_user(db_session, faker)
    location = await create_location(db_session, faker)
    room = await create_room(db_session, faker, location=location)
    await db_session.commit()
    override_admin_token(async_client.app_ref, user_id=user.id)

    monkeypatch.setattr(settings, "S3_PUBLIC_BASE_URL", "http://cdn.local/")
    monkeypatch.setattr(settings, "S3_PUBLIC_BUCKET", "public-uploads")

    async def fake_presign_upload_put(self, bucket, key, content_type, expires):
        return f"http://s3.local/upload/{key}"

    monkeypatch.setattr(FileService, "presign_upload_put", fake_presign_upload_put)

    response1 = await async_client.post(
        f"/rooms/{room.id}/upload_image",
        json={"mime": "image/png", "ext": "png", "size": 123},
        headers=auth_header(),
    )
    response2 = await async_client.post(
        f"/rooms/{room.id}/upload_image",
        json={"mime": "image/png", "ext": "png", "size": 123},
        headers=auth_header(),
    )

    async_client.app_ref.dependency_overrides.clear()
    assert response1.status_code == 200
    assert response2.status_code == 200

    images = (
        await db_session.execute(
            select(Image).where(Image.room_id == room.id)
        )
    ).scalars().all()
    assert len(images) == 2


@pytest.mark.asyncio
async def test__upload_room_image_saves_file_public_url(async_client, db_session, faker, monkeypatch):
    user = await create_user(db_session, faker)
    location = await create_location(db_session, faker)
    room = await create_room(db_session, faker, location=location)
    await db_session.commit()
    override_admin_token(async_client.app_ref, user_id=user.id)

    monkeypatch.setattr(settings, "S3_PUBLIC_BASE_URL", "http://cdn.local/")
    monkeypatch.setattr(settings, "S3_PUBLIC_BUCKET", "public-uploads")

    async def fake_presign_upload_put(self, bucket, key, content_type, expires):
        return f"http://s3.local/upload/{key}"

    monkeypatch.setattr(FileService, "presign_upload_put", fake_presign_upload_put)

    response = await async_client.post(
        f"/rooms/{room.id}/upload_image",
        json={"mime": "image/png", "ext": "png", "size": 123, "original_name": "room.png"},
        headers=auth_header(),
    )

    async_client.app_ref.dependency_overrides.clear()
    assert response.status_code == 200
    payload = response.json()

    stored_image = await db_session.get(Image, payload["id"])
    stored_file = await db_session.get(File, stored_image.file_id)
    assert stored_file.public_url == payload["public_url"]
    assert stored_file.bucket == "public-uploads"


@pytest.mark.asyncio
async def test__upload_room_image_defaults_original_name(async_client, db_session, faker, monkeypatch):
    user = await create_user(db_session, faker)
    location = await create_location(db_session, faker)
    room = await create_room(db_session, faker, location=location)
    await db_session.commit()
    override_admin_token(async_client.app_ref, user_id=user.id)

    monkeypatch.setattr(settings, "S3_PUBLIC_BASE_URL", "http://cdn.local/")
    monkeypatch.setattr(settings, "S3_PUBLIC_BUCKET", "public-uploads")
    monkeypatch.setattr(settings, "FILES_ALLOWED_CONTENT_TYPES", "image/png")

    async def fake_presign_upload_put(self, bucket, key, content_type, expires):
        return f"http://s3.local/upload/{key}"

    monkeypatch.setattr(FileService, "presign_upload_put", fake_presign_upload_put)

    response = await async_client.post(
        f"/rooms/{room.id}/upload_image",
        json={"mime": "image/png", "ext": "png", "size": 123},
        headers=auth_header(),
    )

    async_client.app_ref.dependency_overrides.clear()
    assert response.status_code == 200

    stored_image = await db_session.get(Image, response.json()["id"])
    stored_file = await db_session.get(File, stored_image.file_id)
    assert stored_file.original_name == "image.png"


@pytest.mark.asyncio
async def test__upload_room_image_uses_fallback_public_bucket(
    async_client, db_session, faker, monkeypatch
):
    user = await create_user(db_session, faker)
    location = await create_location(db_session, faker)
    room = await create_room(db_session, faker, location=location)
    await db_session.commit()
    override_admin_token(async_client.app_ref, user_id=user.id)

    monkeypatch.setattr(settings, "S3_PUBLIC_BASE_URL", "http://cdn.local/")
    monkeypatch.setattr(settings, "S3_PUBLIC_BUCKET", None)
    monkeypatch.setattr(settings, "S3_BUCKET", "uploads")
    monkeypatch.setattr(settings, "FILES_ALLOWED_CONTENT_TYPES", "image/png")

    captured = {}

    async def fake_presign_upload_put(self, bucket, key, content_type, expires):
        captured["bucket"] = bucket
        return f"http://s3.local/upload/{key}"

    monkeypatch.setattr(FileService, "presign_upload_put", fake_presign_upload_put)

    response = await async_client.post(
        f"/rooms/{room.id}/upload_image",
        json={"mime": "image/png", "ext": "png", "size": 123},
        headers=auth_header(),
    )

    async_client.app_ref.dependency_overrides.clear()
    assert response.status_code == 200
    payload = response.json()

    stored_image = await db_session.get(Image, payload["id"])
    stored_file = await db_session.get(File, stored_image.file_id)
    assert captured["bucket"] == "uploads"
    assert stored_file.bucket == "uploads"
    assert payload["public_url"].startswith("http://cdn.local/uploads/")


@pytest.mark.asyncio
async def test__upload_location_image_returns_presign(async_client, db_session, faker, monkeypatch):
    user = await create_user(db_session, faker)
    location = await create_location(db_session, faker)
    await db_session.commit()
    override_admin_token(async_client.app_ref, user_id=user.id)

    monkeypatch.setattr(settings, "S3_PUBLIC_BASE_URL", "http://cdn.local/")
    monkeypatch.setattr(settings, "S3_PUBLIC_BUCKET", "public-uploads")
    monkeypatch.setattr(settings, "FILES_ALLOWED_CONTENT_TYPES", "image/png,image/jpeg")

    async def fake_presign_upload_put(self, bucket, key, content_type, expires):
        return f"http://s3.local/upload/{key}"

    monkeypatch.setattr(FileService, "presign_upload_put", fake_presign_upload_put)

    response = await async_client.post(
        f"/locations/{location.id}/upload_image",
        json={"mime": "image/jpeg", "ext": "jpg", "size": 321, "original_name": "loc.jpg"},
        headers=auth_header(),
    )

    async_client.app_ref.dependency_overrides.clear()
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["upload_url"].startswith("http://s3.local/upload/images/locations/")
    assert payload["public_url"].startswith("http://cdn.local/public-uploads/images/locations/")

    stored_image = await db_session.get(Image, payload["id"])
    assert stored_image is not None
    assert stored_image.location_id == location.id
    assert stored_image.type == ImageType.LOCATION
    stored_file = await db_session.get(File, stored_image.file_id)
    assert stored_file.bucket == "public-uploads"


@pytest.mark.asyncio
async def test__upload_location_image_uses_fallback_public_bucket(
    async_client, db_session, faker, monkeypatch
):
    user = await create_user(db_session, faker)
    location = await create_location(db_session, faker)
    await db_session.commit()
    override_admin_token(async_client.app_ref, user_id=user.id)

    monkeypatch.setattr(settings, "S3_PUBLIC_BASE_URL", "http://cdn.local/")
    monkeypatch.setattr(settings, "S3_PUBLIC_BUCKET", None)
    monkeypatch.setattr(settings, "S3_BUCKET", "uploads")
    monkeypatch.setattr(settings, "FILES_ALLOWED_CONTENT_TYPES", "image/png")

    captured = {}

    async def fake_presign_upload_put(self, bucket, key, content_type, expires):
        captured["bucket"] = bucket
        return f"http://s3.local/upload/{key}"

    monkeypatch.setattr(FileService, "presign_upload_put", fake_presign_upload_put)

    response = await async_client.post(
        f"/locations/{location.id}/upload_image",
        json={"mime": "image/png", "ext": "png", "size": 321},
        headers=auth_header(),
    )

    async_client.app_ref.dependency_overrides.clear()
    assert response.status_code == 200
    payload = response.json()

    stored_image = await db_session.get(Image, payload["id"])
    stored_file = await db_session.get(File, stored_image.file_id)
    assert captured["bucket"] == "uploads"
    assert stored_file.bucket == "uploads"
    assert payload["public_url"].startswith("http://cdn.local/uploads/")


@pytest.mark.asyncio
async def test__upload_location_image_saves_file_public_url(async_client, db_session, faker, monkeypatch):
    user = await create_user(db_session, faker)
    location = await create_location(db_session, faker)
    await db_session.commit()
    override_admin_token(async_client.app_ref, user_id=user.id)

    monkeypatch.setattr(settings, "S3_PUBLIC_BASE_URL", "http://cdn.local/")
    monkeypatch.setattr(settings, "S3_PUBLIC_BUCKET", "public-uploads")
    monkeypatch.setattr(settings, "FILES_ALLOWED_CONTENT_TYPES", "image/png,image/jpeg")

    async def fake_presign_upload_put(self, bucket, key, content_type, expires):
        return f"http://s3.local/upload/{key}"

    monkeypatch.setattr(FileService, "presign_upload_put", fake_presign_upload_put)

    response = await async_client.post(
        f"/locations/{location.id}/upload_image",
        json={"mime": "image/png", "ext": "png", "size": 321, "original_name": "loc.png"},
        headers=auth_header(),
    )

    async_client.app_ref.dependency_overrides.clear()
    assert response.status_code == 200
    payload = response.json()

    stored_image = await db_session.get(Image, payload["id"])
    stored_file = await db_session.get(File, stored_image.file_id)
    assert stored_file.public_url == payload["public_url"]
    assert stored_file.bucket == "public-uploads"


@pytest.mark.asyncio
async def test__upload_location_image_defaults_original_name(async_client, db_session, faker, monkeypatch):
    user = await create_user(db_session, faker)
    location = await create_location(db_session, faker)
    await db_session.commit()
    override_admin_token(async_client.app_ref, user_id=user.id)

    monkeypatch.setattr(settings, "S3_PUBLIC_BASE_URL", "http://cdn.local/")
    monkeypatch.setattr(settings, "S3_PUBLIC_BUCKET", "public-uploads")
    monkeypatch.setattr(settings, "FILES_ALLOWED_CONTENT_TYPES", "image/png")

    async def fake_presign_upload_put(self, bucket, key, content_type, expires):
        return f"http://s3.local/upload/{key}"

    monkeypatch.setattr(FileService, "presign_upload_put", fake_presign_upload_put)

    response = await async_client.post(
        f"/locations/{location.id}/upload_image",
        json={"mime": "image/png", "ext": "png", "size": 321},
        headers=auth_header(),
    )

    async_client.app_ref.dependency_overrides.clear()
    assert response.status_code == 200
    payload = response.json()

    stored_image = await db_session.get(Image, payload["id"])
    stored_file = await db_session.get(File, stored_image.file_id)
    assert stored_file.original_name == "image.png"


@pytest.mark.asyncio
async def test__upload_location_image_invalid_content_type(async_client, db_session, faker, monkeypatch):
    user = await create_user(db_session, faker)
    location = await create_location(db_session, faker)
    await db_session.commit()
    override_admin_token(async_client.app_ref, user_id=user.id)

    monkeypatch.setattr(settings, "FILES_ALLOWED_CONTENT_TYPES", "image/png")

    response = await async_client.post(
        f"/locations/{location.id}/upload_image",
        json={"mime": "image/jpeg", "ext": "jpg", "size": 123},
        headers=auth_header(),
    )

    async_client.app_ref.dependency_overrides.clear()
    assert response.status_code == 415


@pytest.mark.asyncio
async def test__upload_location_image_invalid_payload_missing_fields(async_client, db_session, faker):
    user = await create_user(db_session, faker)
    override_admin_token(async_client.app_ref, user_id=user.id)

    response = await async_client.post(
        "/locations/1/upload_image",
        json={"mime": "image/png"},
        headers=auth_header(),
    )

    async_client.app_ref.dependency_overrides.clear()
    assert response.status_code == 422


@pytest.mark.asyncio
async def test__upload_location_image_invalid_payload_types(async_client, db_session, faker):
    user = await create_user(db_session, faker)
    override_admin_token(async_client.app_ref, user_id=user.id)

    response = await async_client.post(
        "/locations/1/upload_image",
        json={"mime": "image/png", "ext": "png", "size": "bad"},
        headers=auth_header(),
    )

    async_client.app_ref.dependency_overrides.clear()
    assert response.status_code == 422


@pytest.mark.asyncio
async def test__upload_location_image_not_found(async_client, db_session, faker):
    user = await create_user(db_session, faker)
    override_admin_token(async_client.app_ref, user_id=user.id)

    response = await async_client.post(
        "/locations/999999/upload_image",
        json={"mime": "image/png", "ext": "png", "size": 123},
        headers=auth_header(),
    )

    async_client.app_ref.dependency_overrides.clear()
    assert response.status_code == 404


@pytest.mark.asyncio
async def test__upload_location_image_invalid_size(async_client, db_session, faker, monkeypatch):
    user = await create_user(db_session, faker)
    location = await create_location(db_session, faker)
    await db_session.commit()
    override_admin_token(async_client.app_ref, user_id=user.id)

    monkeypatch.setattr(settings, "S3_MAX_UPLOAD_BYTES_PRESIGNED", 10)
    monkeypatch.setattr(settings, "FILES_ALLOWED_CONTENT_TYPES", "image/png")

    response = await async_client.post(
        f"/locations/{location.id}/upload_image",
        json={"mime": "image/png", "ext": "png", "size": 11},
        headers=auth_header(),
    )

    async_client.app_ref.dependency_overrides.clear()
    assert response.status_code == 413


@pytest.mark.asyncio
async def test__upload_location_image_invalid_size_zero(async_client, db_session, faker, monkeypatch):
    user = await create_user(db_session, faker)
    location = await create_location(db_session, faker)
    await db_session.commit()
    override_admin_token(async_client.app_ref, user_id=user.id)

    monkeypatch.setattr(settings, "FILES_ALLOWED_CONTENT_TYPES", "image/png")

    response = await async_client.post(
        f"/locations/{location.id}/upload_image",
        json={"mime": "image/png", "ext": "png", "size": 0},
        headers=auth_header(),
    )

    async_client.app_ref.dependency_overrides.clear()
    assert response.status_code == 422


@pytest.mark.asyncio
async def test__upload_location_image_negative_size(async_client, db_session, faker, monkeypatch):
    user = await create_user(db_session, faker)
    location = await create_location(db_session, faker)
    await db_session.commit()
    override_admin_token(async_client.app_ref, user_id=user.id)

    monkeypatch.setattr(settings, "FILES_ALLOWED_CONTENT_TYPES", "image/png")

    response = await async_client.post(
        f"/locations/{location.id}/upload_image",
        json={"mime": "image/png", "ext": "png", "size": -1},
        headers=auth_header(),
    )

    async_client.app_ref.dependency_overrides.clear()
    assert response.status_code == 422


@pytest.mark.asyncio
async def test__upload_location_image_rejects_null_byte_name(async_client, db_session, faker, monkeypatch):
    user = await create_user(db_session, faker)
    location = await create_location(db_session, faker)
    await db_session.commit()
    override_admin_token(async_client.app_ref, user_id=user.id)

    monkeypatch.setattr(settings, "FILES_ALLOWED_CONTENT_TYPES", "image/png")

    response = await async_client.post(
        f"/locations/{location.id}/upload_image",
        json={
            "mime": "image/png",
            "ext": "png",
            "size": 123,
            "original_name": "bad\x00name.png",
        },
        headers=auth_header(),
    )

    async_client.app_ref.dependency_overrides.clear()
    assert response.status_code == 422


@pytest.mark.asyncio
async def test__upload_location_image_sanitizes_original_name(async_client, db_session, faker, monkeypatch):
    user = await create_user(db_session, faker)
    location = await create_location(db_session, faker)
    await db_session.commit()
    override_admin_token(async_client.app_ref, user_id=user.id)

    monkeypatch.setattr(settings, "S3_PUBLIC_BASE_URL", "http://cdn.local/")
    monkeypatch.setattr(settings, "S3_PUBLIC_BUCKET", "public-uploads")
    monkeypatch.setattr(settings, "FILES_ALLOWED_CONTENT_TYPES", "image/png")

    async def fake_presign_upload_put(self, bucket, key, content_type, expires):
        return f"http://s3.local/upload/{key}"

    monkeypatch.setattr(FileService, "presign_upload_put", fake_presign_upload_put)

    original_name = "  ../bad/name.png  "
    response = await async_client.post(
        f"/locations/{location.id}/upload_image",
        json={
            "mime": "image/png",
            "ext": "png",
            "size": 123,
            "original_name": original_name,
        },
        headers=auth_header(),
    )

    async_client.app_ref.dependency_overrides.clear()
    assert response.status_code == 200

    stored_image = await db_session.get(Image, response.json()["id"])
    stored_file = await db_session.get(File, stored_image.file_id)
    assert stored_file.original_name == sanitize_filename(original_name)


@pytest.mark.asyncio
async def test__upload_location_image_allows_multiple(async_client, db_session, faker, monkeypatch):
    user = await create_user(db_session, faker)
    location = await create_location(db_session, faker)
    await db_session.commit()
    override_admin_token(async_client.app_ref, user_id=user.id)

    monkeypatch.setattr(settings, "S3_PUBLIC_BASE_URL", "http://cdn.local/")
    monkeypatch.setattr(settings, "S3_PUBLIC_BUCKET", "public-uploads")
    monkeypatch.setattr(settings, "FILES_ALLOWED_CONTENT_TYPES", "image/png")

    async def fake_presign_upload_put(self, bucket, key, content_type, expires):
        return f"http://s3.local/upload/{key}"

    monkeypatch.setattr(FileService, "presign_upload_put", fake_presign_upload_put)

    response1 = await async_client.post(
        f"/locations/{location.id}/upload_image",
        json={"mime": "image/png", "ext": "png", "size": 123},
        headers=auth_header(),
    )
    response2 = await async_client.post(
        f"/locations/{location.id}/upload_image",
        json={"mime": "image/png", "ext": "png", "size": 123},
        headers=auth_header(),
    )

    async_client.app_ref.dependency_overrides.clear()
    assert response1.status_code == 200
    assert response2.status_code == 200

    images = (
        await db_session.execute(
            select(Image).where(Image.location_id == location.id)
        )
    ).scalars().all()
    assert len(images) == 2


@pytest.mark.asyncio
async def test__delete_image_removes_file_and_image(async_client, db_session, faker, monkeypatch):
    user = await create_user(db_session, faker)
    location = await create_location(db_session, faker)
    room = await create_room(db_session, faker, location=location)
    override_admin_token(async_client.app_ref, user_id=user.id)

    file = File(
        user_id=user.id,
        bucket="public-uploads",
        object_key="images/rooms/1/abc123.png",
        original_name="room.png",
        content_type="image/png",
        size_bytes=123,
        checksum_sha256=None,
        status=FileStatus.PENDING,
        is_public=True,
        public_url="http://cdn.local/public-uploads/images/rooms/1/abc123.png",
        meta={},
    )
    db_session.add(file)
    await db_session.flush()

    image = Image(
        type=ImageType.ROOM,
        image1x=file.public_url,
        image2x=None,
        file_id=file.id,
        room_id=room.id,
        location_id=None,
    )
    db_session.add(image)
    await db_session.commit()
    image_id = image.id
    file_id = file.id

    calls: list[tuple[str, str]] = []

    async def fake_delete_object(self, bucket, key):
        calls.append((bucket, key))

    monkeypatch.setattr(FileService, "delete_object", fake_delete_object)

    response = await async_client.delete(
        f"/images/{image.id}",
        headers=auth_header(),
    )

    async_client.app_ref.dependency_overrides.clear()
    assert response.status_code == 204
    assert calls == [("public-uploads", "images/rooms/1/abc123.png")]
    db_session.expire_all()
    assert await db_session.get(Image, image_id) is None
    assert await db_session.get(File, file_id) is None


@pytest.mark.asyncio
async def test__delete_image_requires_auth(async_client):
    response = await async_client.delete("/images/1")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test__delete_image_requires_admin(async_client, db_session, faker):
    user = await create_user(db_session, faker)
    override_user_token(async_client.app_ref, user_id=user.id)

    response = await async_client.delete(
        "/images/1",
        headers=auth_header(),
    )

    async_client.app_ref.dependency_overrides.clear()
    assert response.status_code == 403


@pytest.mark.asyncio
async def test__delete_image_not_found(async_client, db_session, faker):
    user = await create_user(db_session, faker)
    override_admin_token(async_client.app_ref, user_id=user.id)

    response = await async_client.delete(
        "/images/999999",
        headers=auth_header(),
    )

    async_client.app_ref.dependency_overrides.clear()
    assert response.status_code == 404


@pytest.mark.asyncio
async def test__delete_image_s3_failure_returns_500(async_client, db_session, faker, monkeypatch):
    user = await create_user(db_session, faker)
    location = await create_location(db_session, faker)
    room = await create_room(db_session, faker, location=location)
    override_admin_token(async_client.app_ref, user_id=user.id)

    file = File(
        user_id=user.id,
        bucket="public-uploads",
        object_key="images/rooms/1/abc123.png",
        original_name="room.png",
        content_type="image/png",
        size_bytes=123,
        checksum_sha256=None,
        status=FileStatus.PENDING,
        is_public=True,
        public_url="http://cdn.local/public-uploads/images/rooms/1/abc123.png",
        meta={},
    )
    db_session.add(file)
    await db_session.flush()

    image = Image(
        type=ImageType.ROOM,
        image1x=file.public_url,
        image2x=None,
        file_id=file.id,
        room_id=room.id,
        location_id=None,
    )
    db_session.add(image)
    await db_session.commit()
    image_id = image.id
    file_id = file.id

    async def fake_delete_object(self, bucket, key):
        raise RuntimeError("s3 failure")

    monkeypatch.setattr(FileService, "delete_object", fake_delete_object)

    with pytest.raises(RuntimeError):
        await async_client.delete(
            f"/images/{image.id}",
            headers=auth_header(),
        )

    async_client.app_ref.dependency_overrides.clear()
    db_session.expire_all()
    assert await db_session.get(Image, image_id) is not None
    assert await db_session.get(File, file_id) is not None
