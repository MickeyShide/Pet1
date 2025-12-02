from datetime import datetime, timedelta, timezone

import pytest

from app.models.booking import BookingStatus
from app.repositories.booking import BookingRepository
from app.schemas.booking import SBookingFilters
from app.schemas.timeslot import STimeSlotFilters
from tests.fixtures.factories import (
    create_booking,
    create_location,
    create_room,
    create_timeslot,
    create_user,
)


@pytest.mark.asyncio
async def test__get_all_bookings_with_timeslots__returns_joined_rows_sorted_by_created_at(db_session, faker):
    # Given
    user = await create_user(db_session, faker)
    other_user = await create_user(db_session, faker)
    location = await create_location(db_session, faker)
    room = await create_room(db_session, faker, location=location)
    now = datetime.now(timezone.utc)
    slot_new = await create_timeslot(
        db_session,
        room=room,
        start_datetime=now + timedelta(days=1),
        end_datetime=now + timedelta(days=1, hours=1),
    )
    slot_old_start = now - timedelta(days=1)
    slot_old = await create_timeslot(
        db_session,
        room=room,
        start_datetime=slot_old_start,
        end_datetime=slot_old_start + timedelta(hours=1),
    )
    older_booking = await create_booking(
        db_session,
        user=user,
        room=room,
        timeslot=slot_old,
        created_at=now - timedelta(days=1, minutes=5),
    )
    newer_booking = await create_booking(
        db_session,
        user=user,
        room=room,
        timeslot=slot_new,
        created_at=now + timedelta(days=1, minutes=5),
    )
    slot_extra = await create_timeslot(
        db_session,
        room=room,
        start_datetime=now + timedelta(days=2),
        end_datetime=now + timedelta(days=2, hours=1),
    )
    await create_booking(
        db_session,
        user=other_user,
        room=room,
        timeslot=slot_extra,
        status=BookingStatus.PAID,
    )
    repo = BookingRepository(db_session)

    # When
    rows = await repo.get_all_bookings_with_timeslots(user.id)

    # Then
    assert [booking.id for booking, _ in rows] == [older_booking.id, newer_booking.id]
    assert [slot.id for _, slot in rows] == [slot_old.id, slot_new.id]


@pytest.mark.asyncio
async def test__get_all_bookings_with_timeslots__applies_room_status_and_timeslot_filters(db_session, faker):
    # Given
    user = await create_user(db_session, faker)
    location = await create_location(db_session, faker)
    room_a = await create_room(db_session, faker, location=location)
    room_b = await create_room(db_session, faker, location=location)
    start = datetime.now(timezone.utc)
    slot_a = await create_timeslot(
        db_session,
        room=room_a,
        start_datetime=start,
        end_datetime=start + timedelta(hours=2),
    )
    slot_b = await create_timeslot(
        db_session,
        room=room_b,
        start_datetime=start + timedelta(days=2),
        end_datetime=start + timedelta(days=2, hours=2),
    )
    await create_booking(
        db_session,
        user=user,
        room=room_a,
        timeslot=slot_a,
        status=BookingStatus.CANCELED,
    )
    target_booking = await create_booking(
        db_session,
        user=user,
        room=room_b,
        timeslot=slot_b,
        status=BookingStatus.PAID,
    )
    repo = BookingRepository(db_session)
    booking_filters = SBookingFilters(
        room_id=room_b.id,
        status=BookingStatus.PAID,
    )
    timeslot_filters = STimeSlotFilters(
        start_datetime=slot_b.start_datetime - timedelta(hours=1),
        end_datetime=slot_b.end_datetime + timedelta(hours=1),
    )

    # When
    rows = await repo.get_all_bookings_with_timeslots(
        user.id,
        booking_filters=booking_filters,
        timeslot_filters=timeslot_filters,
    )

    # Then
    assert len(rows) == 1
    booking, timeslot = rows[0]
    assert booking.id == target_booking.id
    assert timeslot.id == slot_b.id
