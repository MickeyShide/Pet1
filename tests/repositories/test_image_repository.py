import pytest
from sqlalchemy.exc import NoResultFound

from app.models.image import ImageType
from app.repositories.image import ImageRepository


@pytest.mark.asyncio
async def test__image_repository_create_and_get_one(db_session):
    repo = ImageRepository(db_session)

    created = await repo.create(image1x="images/room/1.jpg", image2x=None, type=ImageType.ROOM)
    await db_session.commit()

    fetched = await repo.get_one(id=created.id)
    assert fetched.id == created.id
    assert fetched.type == ImageType.ROOM
    assert fetched.image1x == "images/room/1.jpg"


@pytest.mark.asyncio
async def test__image_repository_delete_removes(db_session):
    repo = ImageRepository(db_session)

    created = await repo.create(image1x="images/room/1.jpg", image2x=None, type=ImageType.ROOM)
    await db_session.commit()

    await repo.delete(id=created.id)
    await db_session.commit()

    with pytest.raises(NoResultFound):
        await repo.get_one(id=created.id)
