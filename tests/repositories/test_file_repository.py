import pytest
from sqlalchemy.exc import NoResultFound

from app.models.file import FileStatus
from app.repositories.file import FileRepository
from tests.fixtures.factories import create_user


@pytest.mark.asyncio
async def test__file_repository_create_and_get(db_session, faker):
    user = await create_user(db_session, faker)
    repo = FileRepository(db_session)

    created = await repo.create(
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
    await db_session.commit()

    fetched = await repo.get_one(id=created.id)
    assert fetched.id == created.id
    assert fetched.object_key == "images/rooms/1/abc.png"
    assert fetched.status == FileStatus.PENDING


@pytest.mark.asyncio
async def test__file_repository_update(db_session, faker):
    user = await create_user(db_session, faker)
    repo = FileRepository(db_session)

    created = await repo.create(
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
    await db_session.commit()

    updated = await repo.update_by_id(created.id, status=FileStatus.UPLOADED)
    assert updated.status == FileStatus.UPLOADED


@pytest.mark.asyncio
async def test__file_repository_delete(db_session, faker):
    user = await create_user(db_session, faker)
    repo = FileRepository(db_session)

    created = await repo.create(
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
    await db_session.commit()

    await repo.delete(id=created.id)
    await db_session.commit()

    with pytest.raises(NoResultFound):
        await repo.get_one(id=created.id)
