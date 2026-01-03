from decimal import Decimal

import pytest

from app.repositories.room import RoomRepository
from tests.fixtures.factories import create_location, create_room


@pytest.mark.asyncio
async def test__room_repository_get_hour_price_returns_value(db_session, faker):
    location = await create_location(db_session, faker)
    room = await create_room(
        db_session,
        faker,
        location=location,
        hour_price=Decimal("123.45"),
    )
    await db_session.commit()
    repo = RoomRepository(db_session)

    result = await repo.get_hour_price(room.id)

    assert result == Decimal("123.45")
