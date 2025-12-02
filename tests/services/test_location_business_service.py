import pytest
from sqlalchemy import select

from app.models import Location, Room
from app.services.business.locations import LocationBusinessService
from app.schemas.location import SLocationCreate, SLocationUpdate
from tests.fixtures.factories import (
    create_location,
    create_room,
)


@pytest.mark.asyncio
async def test__get_all_locations__returns_every_location(db_session, faker):
    # Given
    loc_a = await create_location(db_session, faker)
    loc_b = await create_location(db_session, faker)
    await db_session.commit()
    service = LocationBusinessService()

    # When
    locations = await service.get_all()

    # Then
    names = {loc.name for loc in locations}
    assert {loc_a.name, loc_b.name}.issubset(names)


@pytest.mark.asyncio
async def test__get_rooms_by_location_id__returns_all_rooms(db_session, faker):
    # Given
    location = await create_location(db_session, faker)
    room_a = await create_room(db_session, faker, location=location)
    room_b = await create_room(db_session, faker, location=location)
    await db_session.commit()
    service = LocationBusinessService()

    # When
    rooms = await service.get_rooms_by_location_id(location.id)

    # Then
    ids = {room.id for room in rooms}
    assert {room_a.id, room_b.id} == ids


@pytest.mark.asyncio
async def test__delete_by_id__removes_location(db_session, faker):
    # Given
    location = await create_location(db_session, faker)
    await db_session.commit()
    service = LocationBusinessService()

    # When
    await service.delete_by_id(location.id)

    # Then
    stmt = select(Location).where(Location.id == location.id)
    result = (await db_session.execute(stmt)).scalar_one_or_none()
    assert result is None


@pytest.mark.asyncio
async def test__create_location__persists_and_returns_schema(db_session, faker):
    # Given
    service = LocationBusinessService()
    payload = SLocationCreate(
        name="Test HQ",
        address="1 Infinite Loop",
        description="Main office",
    )

    # When
    result = await service.create_location(payload)

    # Then
    assert result.name == payload.name
    stored = (await db_session.execute(select(Location).where(Location.id == result.id))).scalar_one()
    assert stored.address == payload.address


@pytest.mark.asyncio
async def test__update_by_id__applies_partial_fields(db_session, faker):
    # Given
    location = await create_location(db_session, faker)
    await db_session.commit()
    service = LocationBusinessService()
    payload = SLocationUpdate(description="New description")

    # When
    result = await service.update_by_id(location.id, payload)

    # Then
    assert result.description == payload.description
    await db_session.refresh(location)
    assert location.description == payload.description
