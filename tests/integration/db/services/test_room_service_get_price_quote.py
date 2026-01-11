from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from app.services.room import RoomService
from tests.factories import create_location, create_room


@pytest.mark.asyncio
async def test__room_service_get_price_quote__returns_total(db_session, faker):
    location = await create_location(db_session, faker)
    room = await create_room(
        db_session,
        faker,
        location=location,
        hour_price=Decimal("150.00"),
    )
    await db_session.flush()
    service = RoomService(db_session)
    start = datetime(2024, 1, 1, tzinfo=timezone.utc)
    end = start + timedelta(hours=2)

    result = await service.get_price_quote(room.id, start, end)

    assert result == Decimal("300.00")


@pytest.mark.asyncio
async def test__room_service_get_price_quote__rounds_half_up(db_session, faker):
    location = await create_location(db_session, faker)
    room = await create_room(
        db_session,
        faker,
        location=location,
        hour_price=Decimal("10.00"),
    )
    await db_session.flush()
    service = RoomService(db_session)
    start = datetime(2024, 1, 1, tzinfo=timezone.utc)
    end = start + timedelta(minutes=1)

    result = await service.get_price_quote(room.id, start, end)

    assert result == Decimal("0.17")
