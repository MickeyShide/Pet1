import types

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from starlette.exceptions import HTTPException

from app.config import settings
from app.models import File, Image
from app.models.file import FileStatus
from app.models.image import ImageType
from app.schemas.auth import SAccessToken
from app.schemas.image import SImageUploadIn
from app.services.business.images import ImageBusinessService, build_key
from app.services.file import FileService
from app.utils.err.base.not_found import NotFoundException
from app.utils.file_utils import sanitize_filename
from tests.fixtures.factories import create_location, create_room, create_user


def test__build_key_uses_scope_owner_ext(monkeypatch):
    monkeypatch.setattr(
        "app.services.business.images.uuid.uuid4",
        lambda: types.SimpleNamespace(hex="abc123"),
    )

    key = build_key("rooms", 42, "png")

    assert key == "images/rooms/42/abc123.png"


@pytest.mark.asyncio
async def test__upload_room_image_creates_file_and_image(db_session, faker, monkeypatch):
    user = await create_user(db_session, faker)
    location = await create_location(db_session, faker)
    room = await create_room(db_session, faker, location=location)
    await db_session.commit()
    token = SAccessToken(sub=str(user.id), admin=True)

    monkeypatch.setattr(settings, "S3_PUBLIC_BASE_URL", "http://cdn.local/")
    monkeypatch.setattr(settings, "S3_PUBLIC_BUCKET", "public-uploads")
    monkeypatch.setattr(settings, "S3_PRESIGN_EXPIRES_SECONDS", 600)
    monkeypatch.setattr(
        "app.services.business.images.uuid.uuid4",
        lambda: types.SimpleNamespace(hex="abc123"),
    )

    async def fake_presign_upload_put(self, bucket, key, content_type, expires):
        return f"http://s3.local/upload/{key}"

    monkeypatch.setattr(FileService, "presign_upload_put", fake_presign_upload_put)

    payload = SImageUploadIn(mime="image/png", ext="png", size=321, original_name="room.png")
    result = await ImageBusinessService(token_data=token).upload_room_image(room.id, payload)

    assert result.upload_url == f"http://s3.local/upload/images/rooms/{room.id}/abc123.png"
    assert result.public_url == f"http://cdn.local/public-uploads/images/rooms/{room.id}/abc123.png"

    stored_image = await db_session.get(Image, result.id)
    assert stored_image is not None
    assert stored_image.type == ImageType.ROOM
    assert stored_image.room_id == room.id
    assert stored_image.image1x == result.public_url

    stored_file = await db_session.get(File, stored_image.file_id)
    assert stored_file is not None
    assert stored_file.bucket == "public-uploads"
    assert stored_file.object_key == f"images/rooms/{room.id}/abc123.png"
    assert stored_file.public_url == result.public_url
    assert stored_file.status == FileStatus.PENDING
    assert stored_file.is_public is True
    assert stored_file.public_url == result.public_url


@pytest.mark.asyncio
async def test__upload_room_image_rejects_invalid_content_type(db_session, faker, monkeypatch):
    user = await create_user(db_session, faker)
    location = await create_location(db_session, faker)
    room = await create_room(db_session, faker, location=location)
    await db_session.commit()
    token = SAccessToken(sub=str(user.id), admin=True)

    monkeypatch.setattr(settings, "FILES_ALLOWED_CONTENT_TYPES", "image/png")

    payload = SImageUploadIn(mime="image/jpeg", ext="jpg", size=123, original_name="room.jpg")
    with pytest.raises(HTTPException) as exc:
        await ImageBusinessService(token_data=token).upload_room_image(room.id, payload)
    assert exc.value.status_code == 415


@pytest.mark.asyncio
async def test__upload_room_image_room_not_found(db_session, faker):
    user = await create_user(db_session, faker)
    await db_session.commit()
    token = SAccessToken(sub=str(user.id), admin=True)

    payload = SImageUploadIn(mime="image/png", ext="png", size=123, original_name="room.png")
    with pytest.raises(NotFoundException):
        await ImageBusinessService(token_data=token).upload_room_image(999999, payload)


@pytest.mark.asyncio
async def test__upload_room_image_presign_uses_public_bucket(db_session, faker, monkeypatch):
    user = await create_user(db_session, faker)
    location = await create_location(db_session, faker)
    room = await create_room(db_session, faker, location=location)
    await db_session.commit()
    token = SAccessToken(sub=str(user.id), admin=True)

    monkeypatch.setattr(settings, "S3_PUBLIC_BASE_URL", "http://cdn.local/")
    monkeypatch.setattr(settings, "S3_PUBLIC_BUCKET", "public-uploads")
    monkeypatch.setattr(settings, "FILES_ALLOWED_CONTENT_TYPES", "image/png")

    captured = {}

    async def fake_presign_upload_put(self, bucket, key, content_type, expires):
        captured["bucket"] = bucket
        captured["key"] = key
        captured["content_type"] = content_type
        captured["expires"] = expires
        return f"http://s3.local/upload/{key}"

    monkeypatch.setattr(FileService, "presign_upload_put", fake_presign_upload_put)

    payload = SImageUploadIn(mime="image/png", ext="png", size=321, original_name="room.png")
    await ImageBusinessService(token_data=token).upload_room_image(room.id, payload)

    assert captured["bucket"] == "public-uploads"
    assert captured["key"].startswith(f"images/rooms/{room.id}/")
    assert captured["content_type"] == "image/png"


@pytest.mark.asyncio
async def test__upload_room_image_uses_fallback_public_bucket(db_session, faker, monkeypatch):
    user = await create_user(db_session, faker)
    location = await create_location(db_session, faker)
    room = await create_room(db_session, faker, location=location)
    await db_session.commit()
    token = SAccessToken(sub=str(user.id), admin=True)

    monkeypatch.setattr(settings, "S3_PUBLIC_BASE_URL", "http://cdn.local/")
    monkeypatch.setattr(settings, "S3_PUBLIC_BUCKET", None)
    monkeypatch.setattr(settings, "S3_BUCKET", "uploads")
    monkeypatch.setattr(settings, "FILES_ALLOWED_CONTENT_TYPES", "image/png")

    captured = {}

    async def fake_presign_upload_put(self, bucket, key, content_type, expires):
        captured["bucket"] = bucket
        return f"http://s3.local/upload/{key}"

    monkeypatch.setattr(FileService, "presign_upload_put", fake_presign_upload_put)

    payload = SImageUploadIn(mime="image/png", ext="png", size=321, original_name="room.png")
    result = await ImageBusinessService(token_data=token).upload_room_image(room.id, payload)

    stored_image = await db_session.get(Image, result.id)
    stored_file = await db_session.get(File, stored_image.file_id)
    assert captured["bucket"] == "uploads"
    assert stored_file.bucket == "uploads"
    assert result.public_url.startswith("http://cdn.local/uploads/")


@pytest.mark.asyncio
async def test__upload_room_image_rejects_invalid_size(db_session, faker, monkeypatch):
    user = await create_user(db_session, faker)
    location = await create_location(db_session, faker)
    room = await create_room(db_session, faker, location=location)
    await db_session.commit()
    token = SAccessToken(sub=str(user.id), admin=True)

    monkeypatch.setattr(settings, "S3_MAX_UPLOAD_BYTES_PRESIGNED", 100)
    monkeypatch.setattr(settings, "FILES_ALLOWED_CONTENT_TYPES", "image/png")

    payload = SImageUploadIn(mime="image/png", ext="png", size=101, original_name="room.png")
    with pytest.raises(HTTPException) as exc:
        await ImageBusinessService(token_data=token).upload_room_image(room.id, payload)
    assert exc.value.status_code == 413


@pytest.mark.asyncio
async def test__upload_room_image_rejects_zero_size(db_session, faker, monkeypatch):
    user = await create_user(db_session, faker)
    location = await create_location(db_session, faker)
    room = await create_room(db_session, faker, location=location)
    await db_session.commit()
    token = SAccessToken(sub=str(user.id), admin=True)

    monkeypatch.setattr(settings, "FILES_ALLOWED_CONTENT_TYPES", "image/png")

    payload = SImageUploadIn(mime="image/png", ext="png", size=0, original_name="room.png")
    with pytest.raises(HTTPException) as exc:
        await ImageBusinessService(token_data=token).upload_room_image(room.id, payload)
    assert exc.value.status_code == 422


@pytest.mark.asyncio
async def test__upload_room_image_rejects_negative_size(db_session, faker, monkeypatch):
    user = await create_user(db_session, faker)
    location = await create_location(db_session, faker)
    room = await create_room(db_session, faker, location=location)
    await db_session.commit()
    token = SAccessToken(sub=str(user.id), admin=True)

    monkeypatch.setattr(settings, "FILES_ALLOWED_CONTENT_TYPES", "image/png")

    payload = SImageUploadIn(mime="image/png", ext="png", size=-1, original_name="room.png")
    with pytest.raises(HTTPException) as exc:
        await ImageBusinessService(token_data=token).upload_room_image(room.id, payload)
    assert exc.value.status_code == 422


@pytest.mark.asyncio
async def test__upload_location_image_creates_file_and_image(db_session, faker, monkeypatch):
    user = await create_user(db_session, faker)
    location = await create_location(db_session, faker)
    await db_session.commit()
    token = SAccessToken(sub=str(user.id), admin=True)

    monkeypatch.setattr(settings, "S3_PUBLIC_BASE_URL", "http://cdn.local/")
    monkeypatch.setattr(settings, "S3_PUBLIC_BUCKET", "public-uploads")
    monkeypatch.setattr(
        "app.services.business.images.uuid.uuid4",
        lambda: types.SimpleNamespace(hex="abc123"),
    )

    async def fake_presign_upload_put(self, bucket, key, content_type, expires):
        return f"http://s3.local/upload/{key}"

    monkeypatch.setattr(FileService, "presign_upload_put", fake_presign_upload_put)

    payload = SImageUploadIn(mime="image/jpeg", ext="jpg", size=111, original_name="loc.jpg")
    result = await ImageBusinessService(token_data=token).upload_location_image(location.id, payload)

    assert result.upload_url == f"http://s3.local/upload/images/locations/{location.id}/abc123.jpg"
    assert result.public_url == f"http://cdn.local/public-uploads/images/locations/{location.id}/abc123.jpg"

    stored_image = await db_session.get(Image, result.id)
    assert stored_image is not None
    assert stored_image.type == ImageType.LOCATION
    assert stored_image.location_id == location.id
    stored_file = await db_session.get(File, stored_image.file_id)
    assert stored_file.object_key == f"images/locations/{location.id}/abc123.jpg"


@pytest.mark.asyncio
async def test__upload_location_image_presign_uses_public_bucket(db_session, faker, monkeypatch):
    user = await create_user(db_session, faker)
    location = await create_location(db_session, faker)
    await db_session.commit()
    token = SAccessToken(sub=str(user.id), admin=True)

    monkeypatch.setattr(settings, "S3_PUBLIC_BASE_URL", "http://cdn.local/")
    monkeypatch.setattr(settings, "S3_PUBLIC_BUCKET", "public-uploads")
    monkeypatch.setattr(settings, "FILES_ALLOWED_CONTENT_TYPES", "image/png")

    captured = {}

    async def fake_presign_upload_put(self, bucket, key, content_type, expires):
        captured["bucket"] = bucket
        captured["key"] = key
        captured["content_type"] = content_type
        captured["expires"] = expires
        return f"http://s3.local/upload/{key}"

    monkeypatch.setattr(FileService, "presign_upload_put", fake_presign_upload_put)

    payload = SImageUploadIn(mime="image/png", ext="png", size=321, original_name="loc.png")
    await ImageBusinessService(token_data=token).upload_location_image(location.id, payload)

    assert captured["bucket"] == "public-uploads"
    assert captured["key"].startswith(f"images/locations/{location.id}/")
    assert captured["content_type"] == "image/png"


@pytest.mark.asyncio
async def test__upload_location_image_rejects_invalid_content_type(db_session, faker, monkeypatch):
    user = await create_user(db_session, faker)
    location = await create_location(db_session, faker)
    await db_session.commit()
    token = SAccessToken(sub=str(user.id), admin=True)

    monkeypatch.setattr(settings, "FILES_ALLOWED_CONTENT_TYPES", "image/png")

    payload = SImageUploadIn(mime="image/jpeg", ext="jpg", size=123, original_name="loc.jpg")
    with pytest.raises(HTTPException) as exc:
        await ImageBusinessService(token_data=token).upload_location_image(location.id, payload)
    assert exc.value.status_code == 415


@pytest.mark.asyncio
async def test__upload_location_image_defaults_original_name(db_session, faker, monkeypatch):
    user = await create_user(db_session, faker)
    location = await create_location(db_session, faker)
    await db_session.commit()
    token = SAccessToken(sub=str(user.id), admin=True)

    monkeypatch.setattr(settings, "S3_PUBLIC_BASE_URL", "http://cdn.local/")
    monkeypatch.setattr(settings, "S3_PUBLIC_BUCKET", "public-uploads")
    monkeypatch.setattr(settings, "FILES_ALLOWED_CONTENT_TYPES", "image/png")

    async def fake_presign_upload_put(self, bucket, key, content_type, expires):
        return f"http://s3.local/upload/{key}"

    monkeypatch.setattr(FileService, "presign_upload_put", fake_presign_upload_put)

    payload = SImageUploadIn(mime="image/png", ext="png", size=111, original_name=None)
    result = await ImageBusinessService(token_data=token).upload_location_image(location.id, payload)

    stored_image = await db_session.get(Image, result.id)
    stored_file = await db_session.get(File, stored_image.file_id)
    assert stored_file.original_name == "image.png"


@pytest.mark.asyncio
async def test__upload_location_image_rejects_invalid_size(db_session, faker, monkeypatch):
    user = await create_user(db_session, faker)
    location = await create_location(db_session, faker)
    await db_session.commit()
    token = SAccessToken(sub=str(user.id), admin=True)

    monkeypatch.setattr(settings, "S3_MAX_UPLOAD_BYTES_PRESIGNED", 10)
    monkeypatch.setattr(settings, "FILES_ALLOWED_CONTENT_TYPES", "image/png")

    payload = SImageUploadIn(mime="image/png", ext="png", size=11, original_name="loc.png")
    with pytest.raises(HTTPException) as exc:
        await ImageBusinessService(token_data=token).upload_location_image(location.id, payload)
    assert exc.value.status_code == 413


@pytest.mark.asyncio
async def test__upload_location_image_rejects_negative_size(db_session, faker, monkeypatch):
    user = await create_user(db_session, faker)
    location = await create_location(db_session, faker)
    await db_session.commit()
    token = SAccessToken(sub=str(user.id), admin=True)

    monkeypatch.setattr(settings, "FILES_ALLOWED_CONTENT_TYPES", "image/png")

    payload = SImageUploadIn(mime="image/png", ext="png", size=-1, original_name="loc.png")
    with pytest.raises(HTTPException) as exc:
        await ImageBusinessService(token_data=token).upload_location_image(location.id, payload)
    assert exc.value.status_code == 422


@pytest.mark.asyncio
async def test__upload_location_image_truncates_original_name(db_session, faker, monkeypatch):
    user = await create_user(db_session, faker)
    location = await create_location(db_session, faker)
    await db_session.commit()
    token = SAccessToken(sub=str(user.id), admin=True)

    monkeypatch.setattr(settings, "S3_PUBLIC_BASE_URL", "http://cdn.local/")
    monkeypatch.setattr(settings, "S3_PUBLIC_BUCKET", "public-uploads")
    monkeypatch.setattr(settings, "FILES_ALLOWED_CONTENT_TYPES", "image/png")

    async def fake_presign_upload_put(self, bucket, key, content_type, expires):
        return f"http://s3.local/upload/{key}"

    monkeypatch.setattr(FileService, "presign_upload_put", fake_presign_upload_put)

    original_name = "b" * 200 + ".png"
    payload = SImageUploadIn(mime="image/png", ext="png", size=111, original_name=original_name)
    result = await ImageBusinessService(token_data=token).upload_location_image(location.id, payload)

    stored_image = await db_session.get(Image, result.id)
    stored_file = await db_session.get(File, stored_image.file_id)
    assert len(stored_file.original_name) == 120


@pytest.mark.asyncio
async def test__upload_room_image_defaults_original_name(db_session, faker, monkeypatch):
    user = await create_user(db_session, faker)
    location = await create_location(db_session, faker)
    room = await create_room(db_session, faker, location=location)
    await db_session.commit()
    token = SAccessToken(sub=str(user.id), admin=True)

    monkeypatch.setattr(settings, "S3_PUBLIC_BASE_URL", "http://cdn.local/")
    monkeypatch.setattr(settings, "S3_PUBLIC_BUCKET", "public-uploads")
    monkeypatch.setattr(settings, "FILES_ALLOWED_CONTENT_TYPES", "image/png")

    async def fake_presign_upload_put(self, bucket, key, content_type, expires):
        return f"http://s3.local/upload/{key}"

    monkeypatch.setattr(FileService, "presign_upload_put", fake_presign_upload_put)

    payload = SImageUploadIn(mime="image/png", ext="png", size=111, original_name=None)
    result = await ImageBusinessService(token_data=token).upload_room_image(room.id, payload)

    stored_image = await db_session.get(Image, result.id)
    stored_file = await db_session.get(File, stored_image.file_id)
    assert stored_file.original_name == "image.png"


@pytest.mark.asyncio
async def test__upload_location_image_sanitizes_original_name(db_session, faker, monkeypatch):
    user = await create_user(db_session, faker)
    location = await create_location(db_session, faker)
    await db_session.commit()
    token = SAccessToken(sub=str(user.id), admin=True)

    monkeypatch.setattr(settings, "S3_PUBLIC_BASE_URL", "http://cdn.local/")
    monkeypatch.setattr(settings, "S3_PUBLIC_BUCKET", "public-uploads")
    monkeypatch.setattr(settings, "FILES_ALLOWED_CONTENT_TYPES", "image/png")

    async def fake_presign_upload_put(self, bucket, key, content_type, expires):
        return f"http://s3.local/upload/{key}"

    monkeypatch.setattr(FileService, "presign_upload_put", fake_presign_upload_put)

    original_name = "  ../bad/name.png  "
    payload = SImageUploadIn(mime="image/png", ext="png", size=111, original_name=original_name)
    result = await ImageBusinessService(token_data=token).upload_location_image(location.id, payload)

    stored_image = await db_session.get(Image, result.id)
    stored_file = await db_session.get(File, stored_image.file_id)
    assert stored_file.original_name == sanitize_filename(original_name)


@pytest.mark.asyncio
async def test__upload_room_image_sanitizes_original_name(db_session, faker, monkeypatch):
    user = await create_user(db_session, faker)
    location = await create_location(db_session, faker)
    room = await create_room(db_session, faker, location=location)
    await db_session.commit()
    token = SAccessToken(sub=str(user.id), admin=True)

    monkeypatch.setattr(settings, "S3_PUBLIC_BASE_URL", "http://cdn.local/")
    monkeypatch.setattr(settings, "S3_PUBLIC_BUCKET", "public-uploads")
    monkeypatch.setattr(settings, "FILES_ALLOWED_CONTENT_TYPES", "image/png")

    async def fake_presign_upload_put(self, bucket, key, content_type, expires):
        return f"http://s3.local/upload/{key}"

    monkeypatch.setattr(FileService, "presign_upload_put", fake_presign_upload_put)

    original_name = "  ../bad/name.png  "
    payload = SImageUploadIn(mime="image/png", ext="png", size=111, original_name=original_name)
    result = await ImageBusinessService(token_data=token).upload_room_image(room.id, payload)

    stored_image = await db_session.get(Image, result.id)
    stored_file = await db_session.get(File, stored_image.file_id)
    assert stored_file.original_name == sanitize_filename(original_name)


@pytest.mark.asyncio
async def test__upload_room_image_truncates_original_name(db_session, faker, monkeypatch):
    user = await create_user(db_session, faker)
    location = await create_location(db_session, faker)
    room = await create_room(db_session, faker, location=location)
    await db_session.commit()
    token = SAccessToken(sub=str(user.id), admin=True)

    monkeypatch.setattr(settings, "S3_PUBLIC_BASE_URL", "http://cdn.local/")
    monkeypatch.setattr(settings, "S3_PUBLIC_BUCKET", "public-uploads")
    monkeypatch.setattr(settings, "FILES_ALLOWED_CONTENT_TYPES", "image/png")

    async def fake_presign_upload_put(self, bucket, key, content_type, expires):
        return f"http://s3.local/upload/{key}"

    monkeypatch.setattr(FileService, "presign_upload_put", fake_presign_upload_put)

    original_name = "a" * 200 + ".png"
    payload = SImageUploadIn(mime="image/png", ext="png", size=111, original_name=original_name)
    result = await ImageBusinessService(token_data=token).upload_room_image(room.id, payload)

    stored_image = await db_session.get(Image, result.id)
    stored_file = await db_session.get(File, stored_image.file_id)
    assert len(stored_file.original_name) == 120


@pytest.mark.asyncio
async def test__upload_room_image_rejects_null_byte_name(db_session, faker, monkeypatch):
    user = await create_user(db_session, faker)
    location = await create_location(db_session, faker)
    room = await create_room(db_session, faker, location=location)
    await db_session.commit()
    token = SAccessToken(sub=str(user.id), admin=True)

    monkeypatch.setattr(settings, "FILES_ALLOWED_CONTENT_TYPES", "image/png")

    payload = SImageUploadIn(mime="image/png", ext="png", size=111, original_name="bad\x00name.png")
    with pytest.raises(HTTPException) as exc:
        await ImageBusinessService(token_data=token).upload_room_image(room.id, payload)
    assert exc.value.status_code == 422


@pytest.mark.asyncio
async def test__upload_location_image_not_found(db_session, faker):
    user = await create_user(db_session, faker)
    await db_session.commit()
    token = SAccessToken(sub=str(user.id), admin=True)

    payload = SImageUploadIn(mime="image/png", ext="png", size=111, original_name="loc.png")
    with pytest.raises(NotFoundException):
        await ImageBusinessService(token_data=token).upload_location_image(999999, payload)


@pytest.mark.asyncio
async def test__upload_room_image_requires_user(db_session, faker):
    location = await create_location(db_session, faker)
    room = await create_room(db_session, faker, location=location)
    await db_session.commit()

    payload = SImageUploadIn(mime="image/png", ext="png", size=111, original_name="room.png")
    with pytest.raises(IntegrityError):
        await ImageBusinessService(token_data=None).upload_room_image(room.id, payload)


@pytest.mark.asyncio
async def test__upload_location_image_requires_user(db_session, faker):
    location = await create_location(db_session, faker)
    await db_session.commit()

    payload = SImageUploadIn(mime="image/png", ext="png", size=111, original_name="loc.png")
    with pytest.raises(IntegrityError):
        await ImageBusinessService(token_data=None).upload_location_image(location.id, payload)


@pytest.mark.asyncio
async def test__delete_image_removes_file_and_image(db_session, faker, monkeypatch):
    user = await create_user(db_session, faker)
    location = await create_location(db_session, faker)
    room = await create_room(db_session, faker, location=location)
    token = SAccessToken(sub=str(user.id), admin=True)

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

    await ImageBusinessService(token_data=token).delete_image(image.id)

    assert calls == [("public-uploads", "images/rooms/1/abc123.png")]
    db_session.expire_all()
    assert await db_session.get(Image, image_id) is None
    assert await db_session.get(File, file_id) is None


@pytest.mark.asyncio
async def test__delete_location_image_removes_file_and_image(db_session, faker, monkeypatch):
    user = await create_user(db_session, faker)
    location = await create_location(db_session, faker)
    token = SAccessToken(sub=str(user.id), admin=True)

    file = File(
        user_id=user.id,
        bucket="public-uploads",
        object_key="images/locations/1/loc.png",
        original_name="loc.png",
        content_type="image/png",
        size_bytes=123,
        checksum_sha256=None,
        status=FileStatus.PENDING,
        is_public=True,
        public_url="http://cdn.local/public-uploads/images/locations/1/loc.png",
        meta={},
    )
    db_session.add(file)
    await db_session.flush()

    image = Image(
        type=ImageType.LOCATION,
        image1x=file.public_url,
        image2x=None,
        file_id=file.id,
        room_id=None,
        location_id=location.id,
    )
    db_session.add(image)
    await db_session.commit()
    image_id = image.id
    file_id = file.id

    calls: list[tuple[str, str]] = []

    async def fake_delete_object(self, bucket, key):
        calls.append((bucket, key))

    monkeypatch.setattr(FileService, "delete_object", fake_delete_object)

    await ImageBusinessService(token_data=token).delete_image(image.id)

    assert calls == [("public-uploads", "images/locations/1/loc.png")]
    db_session.expire_all()
    assert await db_session.get(Image, image_id) is None
    assert await db_session.get(File, file_id) is None


@pytest.mark.asyncio
async def test__delete_image_handles_non_public_file(db_session, faker, monkeypatch):
    user = await create_user(db_session, faker)
    location = await create_location(db_session, faker)
    room = await create_room(db_session, faker, location=location)
    token = SAccessToken(sub=str(user.id), admin=True)

    file = File(
        user_id=user.id,
        bucket="private-uploads",
        object_key="images/rooms/1/private.png",
        original_name="room.png",
        content_type="image/png",
        size_bytes=123,
        checksum_sha256=None,
        status=FileStatus.PENDING,
        is_public=False,
        public_url=None,
        meta={},
    )
    db_session.add(file)
    await db_session.flush()

    image = Image(
        type=ImageType.ROOM,
        image1x="http://cdn.local/private.png",
        image2x=None,
        file_id=file.id,
        room_id=room.id,
        location_id=None,
    )
    db_session.add(image)
    await db_session.commit()

    calls: list[tuple[str, str]] = []

    async def fake_delete_object(self, bucket, key):
        calls.append((bucket, key))

    monkeypatch.setattr(FileService, "delete_object", fake_delete_object)

    await ImageBusinessService(token_data=token).delete_image(image.id)

    assert calls == [("private-uploads", "images/rooms/1/private.png")]


@pytest.mark.asyncio
async def test__delete_image_s3_failure_keeps_records(db_session, faker, monkeypatch):
    user = await create_user(db_session, faker)
    location = await create_location(db_session, faker)
    room = await create_room(db_session, faker, location=location)
    token = SAccessToken(sub=str(user.id), admin=True)

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

    async def fake_delete_object(self, bucket, key):
        raise RuntimeError("s3 failure")

    monkeypatch.setattr(FileService, "delete_object", fake_delete_object)

    with pytest.raises(RuntimeError):
        await ImageBusinessService(token_data=token).delete_image(image.id)

    assert await db_session.get(Image, image.id) is not None
    assert await db_session.get(File, file.id) is not None


@pytest.mark.asyncio
async def test__delete_image_multiple_images_same_room(db_session, faker, monkeypatch):
    user = await create_user(db_session, faker)
    location = await create_location(db_session, faker)
    room = await create_room(db_session, faker, location=location)
    token = SAccessToken(sub=str(user.id), admin=True)

    file1 = File(
        user_id=user.id,
        bucket="public-uploads",
        object_key="images/rooms/1/a.png",
        original_name="a.png",
        content_type="image/png",
        size_bytes=123,
        checksum_sha256=None,
        status=FileStatus.PENDING,
        is_public=True,
        public_url="http://cdn.local/public-uploads/images/rooms/1/a.png",
        meta={},
    )
    file2 = File(
        user_id=user.id,
        bucket="public-uploads",
        object_key="images/rooms/1/b.png",
        original_name="b.png",
        content_type="image/png",
        size_bytes=123,
        checksum_sha256=None,
        status=FileStatus.PENDING,
        is_public=True,
        public_url="http://cdn.local/public-uploads/images/rooms/1/b.png",
        meta={},
    )
    db_session.add(file1)
    db_session.add(file2)
    await db_session.flush()

    image1 = Image(
        type=ImageType.ROOM,
        image1x=file1.public_url,
        image2x=None,
        file_id=file1.id,
        room_id=room.id,
        location_id=None,
    )
    image2 = Image(
        type=ImageType.ROOM,
        image1x=file2.public_url,
        image2x=None,
        file_id=file2.id,
        room_id=room.id,
        location_id=None,
    )
    db_session.add(image1)
    db_session.add(image2)
    await db_session.commit()

    calls: list[tuple[str, str]] = []

    async def fake_delete_object(self, bucket, key):
        calls.append((bucket, key))

    monkeypatch.setattr(FileService, "delete_object", fake_delete_object)

    await ImageBusinessService(token_data=token).delete_image(image1.id)

    assert calls == [("public-uploads", "images/rooms/1/a.png")]
    remaining = await db_session.get(Image, image2.id)
    assert remaining is not None


@pytest.mark.asyncio
async def test__upload_room_image_allows_multiple_images(db_session, faker, monkeypatch):
    user = await create_user(db_session, faker)
    location = await create_location(db_session, faker)
    room = await create_room(db_session, faker, location=location)
    await db_session.commit()
    token = SAccessToken(sub=str(user.id), admin=True)

    monkeypatch.setattr(settings, "S3_PUBLIC_BASE_URL", "http://cdn.local/")
    monkeypatch.setattr(settings, "S3_PUBLIC_BUCKET", "public-uploads")
    monkeypatch.setattr(settings, "FILES_ALLOWED_CONTENT_TYPES", "image/png")

    async def fake_presign_upload_put(self, bucket, key, content_type, expires):
        return f"http://s3.local/upload/{key}"

    monkeypatch.setattr(FileService, "presign_upload_put", fake_presign_upload_put)

    payload = SImageUploadIn(mime="image/png", ext="png", size=111, original_name="room.png")
    await ImageBusinessService(token_data=token).upload_room_image(room.id, payload)
    await ImageBusinessService(token_data=token).upload_room_image(room.id, payload)

    result = await db_session.execute(select(Image).where(Image.room_id == room.id))
    assert len(result.scalars().all()) == 2


@pytest.mark.asyncio
async def test__delete_image_missing_raises(db_session, faker):
    user = await create_user(db_session, faker)
    await db_session.commit()
    token = SAccessToken(sub=str(user.id), admin=True)

    with pytest.raises(NotFoundException):
        await ImageBusinessService(token_data=token).delete_image(999999)
