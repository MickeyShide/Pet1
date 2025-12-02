from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy.exc import NoResultFound

from app.models.booking import BookingStatus
from app.repositories.timeslot import TimeSlotRepository
from tests.fixtures.factories import (
    create_booking,
    create_location,
    create_room,
    create_timeslot,
    create_user,
)


@pytest.mark.asyncio
async def test__lock_time_slot_repo__returns_flag_for_active_booking(db_session, faker):
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
    repo = TimeSlotRepository(db_session)

    # When
    timeslot, has_active_booking = await repo.lock_time_slot_for_booking(slot.id)

    # Then
    assert timeslot.id == slot.id
    assert has_active_booking is True


@pytest.mark.asyncio
async def test__lock_time_slot_repo__ignores_canceled_booking(db_session, faker):
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
        status=BookingStatus.CANCELED,
    )
    repo = TimeSlotRepository(db_session)

    # When
    timeslot, has_active_booking = await repo.lock_time_slot_for_booking(slot.id)

    # Then
    assert timeslot.id == slot.id
    assert has_active_booking is False


@pytest.mark.asyncio
async def test__lock_time_slot_repo__raises_not_found_for_missing_slot(db_session):
    repo = TimeSlotRepository(db_session)
    with pytest.raises(NoResultFound):
        await repo.lock_time_slot_for_booking(timeslot_id=9999)
