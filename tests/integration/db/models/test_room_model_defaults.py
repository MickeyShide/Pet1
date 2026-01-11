from decimal import Decimal

import pytest
from sqlalchemy import select

from app.models.room import Room, TimeSlotType
from tests.factories import create_location, create_room


@pytest.mark.asyncio
async def test__room_defaults_time_slot_type(db_session, faker):
    # Given
    location = await create_location(db_session, faker)
    room = await create_room(
        db_session,
        faker,
        location=location,
        name="Green",
        capacity=3,
        description="Small room",
        hour_price=Decimal("50.00"),
        is_active=True,
    )

    # Then
    assert room.time_slot_type == TimeSlotType.FLEXIBLE
    stored = (await db_session.execute(select(Room).where(Room.id == room.id))).scalar_one()
    assert stored.time_slot_type == TimeSlotType.FLEXIBLE
