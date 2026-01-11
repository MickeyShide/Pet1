import pytest

from app.models.file import FileStatus
from tests.factories import create_file, create_user


@pytest.mark.asyncio
async def test__file_persists_public_url(db_session, faker):
    user = await create_user(db_session, faker)
    file = await create_file(
        db_session,
        user=user,
        bucket="public-uploads",
        object_key="images/rooms/1/abc.png",
        original_name="room.png",
        content_type="image/png",
        size_bytes=123,
        checksum_sha256=None,
        status=FileStatus.PENDING,
        is_public=True,
        public_url="http://cdn.local/public-uploads/images/rooms/1/abc.png",
    )

    assert file.id is not None
    assert file.public_url is not None


@pytest.mark.asyncio
async def test__file_allows_null_public_url(db_session, faker):
    user = await create_user(db_session, faker)
    file = await create_file(
        db_session,
        user=user,
        bucket="uploads",
        object_key="images/rooms/1/abc.png",
        original_name="room.png",
        content_type="image/png",
        size_bytes=123,
        checksum_sha256=None,
        status=FileStatus.PENDING,
        is_public=False,
        public_url=None,
    )

    assert file.id is not None
    assert file.public_url is None
