import pytest

from app.models.file import File, FileStatus
from app.models.image import Image, ImageType
from tests.fixtures.factories import create_user


@pytest.mark.asyncio
async def test__image_persists_with_room_type(db_session, faker):
    user = await create_user(db_session, faker)
    file = File(
        user_id=user.id,
        bucket="public-uploads",
        object_key="images/rooms/1/abc.png",
        original_name="room.png",
        content_type="image/png",
        size_bytes=123,
        checksum_sha256=None,
        status=FileStatus.PENDING,
        is_public=True,
        public_url="http://cdn.local/public-uploads/images/rooms/1/abc.png",
        meta={},
    )
    db_session.add(file)
    await db_session.flush()

    image = Image(
        image1x="/img/1x.png",
        image2x=None,
        type=ImageType.ROOM,
        file_id=file.id,
    )

    # When
    db_session.add(image)
    await db_session.commit()

    # Then
    assert image.id is not None
    assert image.type == ImageType.ROOM


@pytest.mark.asyncio
async def test__image_allows_null_paths(db_session, faker):
    user = await create_user(db_session, faker)
    file = File(
        user_id=user.id,
        bucket="public-uploads",
        object_key="images/locations/1/abc.png",
        original_name="loc.png",
        content_type="image/png",
        size_bytes=123,
        checksum_sha256=None,
        status=FileStatus.PENDING,
        is_public=True,
        public_url="http://cdn.local/public-uploads/images/locations/1/abc.png",
        meta={},
    )
    db_session.add(file)
    await db_session.flush()

    image = Image(
        image1x=None,
        image2x=None,
        type=ImageType.LOCATION,
        file_id=file.id,
    )

    # When
    db_session.add(image)
    await db_session.commit()

    # Then
    assert image.id is not None
    assert image.image1x is None
    assert image.image2x is None
