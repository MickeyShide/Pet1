import pytest

from app.services.room import RoomService
from tests.fixtures.factories import create_location, create_room


@pytest.mark.asyncio
async def test__room_service_get_all_with_location(db_session, faker):
    # Given
    location = await create_location(db_session, faker)
    room = await create_room(db_session, faker, location=location)
    await db_session.commit()
    service = RoomService(db_session)

    # When
    result = await service.get_all_with_location()

    # Then
    assert result
    assert result[0].id == room.id
    assert result[0].location.id == location.id
