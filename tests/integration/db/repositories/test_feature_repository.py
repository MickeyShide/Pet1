import pytest
from sqlalchemy.exc import NoResultFound

from app.models.feature import FeatureType
from app.repositories.feature import FeatureRepository
from tests.factories import create_location, create_room


@pytest.mark.asyncio
async def test__feature_repository_create_and_get_one(db_session, faker):
    location = await create_location(db_session, faker)
    room = await create_room(db_session, faker, location=location)
    repo = FeatureRepository(db_session)

    created = await repo.create(name="Projector", type=FeatureType.ROOM, room_id=room.id)
    await db_session.flush()

    fetched = await repo.get_one(id=created.id)
    assert fetched.id == created.id
    assert fetched.room_id == room.id


@pytest.mark.asyncio
async def test__feature_repository_delete_removes(db_session, faker):
    location = await create_location(db_session, faker)
    room = await create_room(db_session, faker, location=location)
    repo = FeatureRepository(db_session)

    created = await repo.create(name="Projector", type=FeatureType.ROOM, room_id=room.id)
    await db_session.flush()

    await repo.delete(id=created.id)
    await db_session.flush()

    with pytest.raises(NoResultFound):
        await repo.get_one(id=created.id)
