from datetime import datetime, timedelta, timezone

import pytest

from app.models.booking import BookingStatus
from app.services.timeslot import TimeSlotService
from app.utils.err.booking import SlotAlreadyTaken, TimeSlotNotFound
from tests.fixtures.factories import (
    create_booking,
    create_location,
    create_room,
    create_timeslot,
    create_user,
)


@pytest.mark.asyncio
async def test__lock_time_slot_for_booking__returns_slot_if_available(db_session, faker):
    # Given
    user = await create_user(db_session, faker)
    location = await create_location(db_session, faker)
    room = await create_room(db_session, faker, location=location)
    start = datetime.now(timezone.utc)
    slot = await create_timeslot(
        db_session,
        room=room,
        start_datetime=start,
        end_datetime=start + timedelta(hours=1),
    )
    await db_session.commit()
    service = TimeSlotService(db_session)

    # When
    locked_slot = await service.lock_time_slot_for_booking(slot.id)

    # Then
    assert locked_slot.id == slot.id
    assert locked_slot.room_id == room.id


@pytest.mark.asyncio
async def test__lock_time_slot_for_booking__raises_not_found_for_missing_slot(db_session):
    # Given
    service = TimeSlotService(db_session)

    # When / Then
    with pytest.raises(TimeSlotNotFound):
        await service.lock_time_slot_for_booking(timeslot_id=9999)


@pytest.mark.asyncio
async def test__lock_time_slot_for_booking__raises_conflict_when_active_booking_exists(db_session, faker):
    # Given
    user = await create_user(db_session, faker)
    location = await create_location(db_session, faker)
    room = await create_room(db_session, faker, location=location)
    start = datetime.now(timezone.utc)
    slot = await create_timeslot(
        db_session,
        room=room,
        start_datetime=start,
        end_datetime=start + timedelta(hours=1),
    )
    await create_booking(
        db_session,
        user=user,
        room=room,
        timeslot=slot,
        status=BookingStatus.PAID,
    )
    await db_session.commit()
    service = TimeSlotService(db_session)

    # When / Then
    with pytest.raises(SlotAlreadyTaken):
        await service.lock_time_slot_for_booking(slot.id)
