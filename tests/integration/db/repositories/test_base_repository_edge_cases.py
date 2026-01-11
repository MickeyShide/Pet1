import pytest
from sqlalchemy.exc import NoResultFound

from app.repositories.location import LocationRepository


@pytest.mark.asyncio
async def test_get_all_with_limit_zero_returns_empty(db_session, faker):
    repo = LocationRepository(db_session)
    await repo.create(name="loc-a", address=faker.address(), description="desc")
    await repo.create(name="loc-b", address=faker.address(), description="desc")

    results = await repo.get_all(limit=0)

    assert results == []


@pytest.mark.asyncio
async def test_get_all_with_offset_zero_returns_all(db_session, faker):
    repo = LocationRepository(db_session)
    first = await repo.create(name="loc-a", address=faker.address(), description="desc")
    second = await repo.create(name="loc-b", address=faker.address(), description="desc")

    results = await repo.get_all(offset=0, desc=False)

    assert [loc.id for loc in results] == [first.id, second.id]


@pytest.mark.asyncio
async def test_delete_raises_no_result_when_missing(db_session):
    repo = LocationRepository(db_session)

    with pytest.raises(NoResultFound):
        await repo.delete(id=99999)


@pytest.mark.asyncio
async def test_update_by_id_raises_no_result_when_missing(db_session):
    repo = LocationRepository(db_session)

    with pytest.raises(NoResultFound):
        await repo.update_by_id(99999, name="missing")
