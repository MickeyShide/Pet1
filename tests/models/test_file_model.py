import pytest

from app.models.file import File, FileStatus
from tests.fixtures.factories import create_user


@pytest.mark.asyncio
async def test__file_persists_public_url(db_session, faker):
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
    await db_session.commit()

    assert file.id is not None
    assert file.public_url is not None


@pytest.mark.asyncio
async def test__file_allows_null_public_url(db_session, faker):
    user = await create_user(db_session, faker)
    file = File(
        user_id=user.id,
        bucket="uploads",
        object_key="images/rooms/1/abc.png",
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
    await db_session.commit()

    assert file.id is not None
    assert file.public_url is None
