from datetime import datetime, timedelta, timezone

import pytest

from app.models.booking import BookingStatus
from app.schemas.auth import SAccessToken
from app.schemas.booking import SBookingFilters
from app.schemas.timeslot import STimeSlotFilters
from app.services.business.bookings import BookingsBusinessService
from tests.fixtures.factories import (
    create_booking,
    create_location,
    create_room,
    create_timeslot,
    create_user,
)


@pytest.mark.asyncio
async def test__get_my_bookings__returns_serialized_payload(db_session, faker):
    # Given
    user = await create_user(db_session, faker)
    location = await create_location(db_session, faker)
    room = await create_room(db_session, faker, location=location)
    slot_start = datetime.now(timezone.utc)
    slot = await create_timeslot(
        db_session,
        room=room,
        start_datetime=slot_start,
        end_datetime=slot_start + timedelta(hours=2),
    )
    booking = await create_booking(db_session, user=user, room=room, timeslot=slot)
    await db_session.commit()
    service = BookingsBusinessService(token_data=SAccessToken(sub=str(user.id), admin=False))

    # When
    result = await service.get_my_bookings()

    # Then
    assert len(result) == 1
    assert result[0].booking.id == booking.id
    assert result[0].timeslot.id == slot.id


@pytest.mark.asyncio
async def test__get_my_bookings__applies_filters_and_excludes_other_users(db_session, faker):
    # Given
    user = await create_user(db_session, faker)
    other_user = await create_user(db_session, faker)
    location = await create_location(db_session, faker)
    room_one = await create_room(db_session, faker, location=location)
    room_two = await create_room(db_session, faker, location=location)
    start = datetime.now(timezone.utc)
    slot_one = await create_timeslot(
        db_session,
        room=room_one,
        start_datetime=start,
        end_datetime=start + timedelta(hours=1),
    )
    slot_two = await create_timeslot(
        db_session,
        room=room_two,
        start_datetime=start + timedelta(days=1),
        end_datetime=start + timedelta(days=1, hours=1),
    )
    other_slot = await create_timeslot(
        db_session,
        room=room_two,
        start_datetime=start + timedelta(days=2),
        end_datetime=start + timedelta(days=2, hours=1),
    )
    await create_booking(
        db_session,
        user=other_user,
        room=room_two,
        timeslot=other_slot,
        status=BookingStatus.PAID,
    )
    await create_booking(
        db_session,
        user=user,
        room=room_one,
        timeslot=slot_one,
        status=BookingStatus.CANCELED,
    )
    matched_booking = await create_booking(
        db_session,
        user=user,
        room=room_two,
        timeslot=slot_two,
        status=BookingStatus.PAID,
    )
    await db_session.commit()
    booking_filters = SBookingFilters(
        room_id=room_two.id,
        status=BookingStatus.PAID,
    )
    timeslot_filters = STimeSlotFilters(
        start_datetime=slot_two.start_datetime - timedelta(minutes=15),
        end_datetime=slot_two.end_datetime + timedelta(minutes=15),
    )
    service = BookingsBusinessService(token_data=SAccessToken(sub=str(user.id), admin=False))

    # When
    result = await service.get_my_bookings(
        booking_filters=booking_filters,
        timeslot_filters=timeslot_filters,
    )

    # Then
    assert len(result) == 1
    assert result[0].booking.id == matched_booking.id
