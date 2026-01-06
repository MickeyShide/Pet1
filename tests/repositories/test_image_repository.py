import pytest
from sqlalchemy.exc import NoResultFound

from app.models.file import File, FileStatus
from app.models.image import ImageType
from app.repositories.image import ImageRepository
from tests.fixtures.factories import create_user


@pytest.mark.asyncio
async def test__image_repository_create_and_get_one(db_session, faker):
    repo = ImageRepository(db_session)

    user = await create_user(db_session, faker)
    file = File(
        user_id=user.id,
        bucket="public-uploads",
        object_key="images/room/1.jpg",
        original_name="room.jpg",
        content_type="image/jpeg",
        size_bytes=123,
        checksum_sha256=None,
        status=FileStatus.PENDING,
        is_public=True,
        public_url="http://cdn.local/public-uploads/images/room/1.jpg",
        meta={},
    )
    db_session.add(file)
    await db_session.flush()

    created = await repo.create(
        image1x="images/room/1.jpg",
        image2x=None,
        type=ImageType.ROOM,
        file_id=file.id,
    )
    await db_session.commit()

    fetched = await repo.get_one(id=created.id)
    assert fetched.id == created.id
    assert fetched.type == ImageType.ROOM
    assert fetched.image1x == "images/room/1.jpg"


@pytest.mark.asyncio
async def test__image_repository_delete_removes(db_session, faker):
    repo = ImageRepository(db_session)

    user = await create_user(db_session, faker)
    file = File(
        user_id=user.id,
        bucket="public-uploads",
        object_key="images/room/1.jpg",
        original_name="room.jpg",
        content_type="image/jpeg",
        size_bytes=123,
        checksum_sha256=None,
        status=FileStatus.PENDING,
        is_public=True,
        public_url="http://cdn.local/public-uploads/images/room/1.jpg",
        meta={},
    )
    db_session.add(file)
    await db_session.flush()

    created = await repo.create(
        image1x="images/room/1.jpg",
        image2x=None,
        type=ImageType.ROOM,
        file_id=file.id,
    )
    await db_session.commit()

    await repo.delete(id=created.id)
    await db_session.commit()

    with pytest.raises(NoResultFound):
        await repo.get_one(id=created.id)
