import pytest

from app.repositories.room import RoomRepository
from tests.fixtures.factories import create_location, create_room


@pytest.mark.asyncio
async def test__get_all_with_location__returns_related_location(db_session, faker):
    # Given
    location = await create_location(db_session, faker)
    room = await create_room(db_session, faker, location=location)
    await db_session.commit()
    repo = RoomRepository(db_session)

    # When
    rooms = await repo.get_all_with_location()

    # Then
    assert rooms
    target = next(item for item in rooms if item.id == room.id)
    assert target.location is not None
    assert target.location.id == location.id


@pytest.mark.asyncio
async def test__get_all_with_location__filters_and_orders(db_session, faker):
    # Given
    location = await create_location(db_session, faker)
    active_room = await create_room(db_session, faker, location=location, is_active=True)
    await create_room(db_session, faker, location=location, is_active=False)
    await db_session.commit()
    repo = RoomRepository(db_session)

    # When
    rooms = await repo.get_all_with_location(is_active=True, desc=False)

    # Then
    ids = [room.id for room in rooms]
    assert ids == sorted(ids)
    assert ids == [active_room.id]


@pytest.mark.asyncio
async def test__get_all_with_location__applies_offset_and_limit(db_session, faker):
    # Given
    location = await create_location(db_session, faker)
    room_a = await create_room(db_session, faker, location=location)
    room_b = await create_room(db_session, faker, location=location)
    room_c = await create_room(db_session, faker, location=location)
    await db_session.commit()
    repo = RoomRepository(db_session)
    ordered_ids = sorted([room_a.id, room_b.id, room_c.id], reverse=True)

    # When
    rooms = await repo.get_all_with_location(offset=1, limit=1)

    # Then
    assert [room.id for room in rooms] == ordered_ids[1:2]
