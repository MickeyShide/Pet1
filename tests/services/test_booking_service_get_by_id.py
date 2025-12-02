from datetime import datetime, timedelta, timezone

import pytest

from app.services.booking import BookingService
from app.utils.err.base.not_found import NotFoundException
from tests.fixtures.factories import (
    create_booking,
    create_location,
    create_room,
    create_timeslot,
    create_user,
)


@pytest.mark.asyncio
async def test__get_booking_with_timeslots_by_id__returns_tuple(db_session, faker):
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
    booking = await create_booking(db_session, user=user, room=room, timeslot=slot)
    await db_session.commit()
    service = BookingService(db_session)

    # When
    found_booking, found_slot = await service.get_booking_with_timeslots_by_id(
        booking_id=booking.id, user_id=user.id, is_admin=False
    )

    # Then
    assert found_booking.id == booking.id
    assert found_slot.id == slot.id


@pytest.mark.asyncio
async def test__get_booking_with_timeslots_by_id__admin_can_view_others(db_session, faker):
    # Given
    admin = await create_user(db_session, faker)
    other = await create_user(db_session, faker)
    location = await create_location(db_session, faker)
    room = await create_room(db_session, faker, location=location)
    start = datetime.now(timezone.utc)
    slot = await create_timeslot(
        db_session,
        room=room,
        start_datetime=start,
        end_datetime=start + timedelta(hours=1),
    )
    booking = await create_booking(db_session, user=other, room=room, timeslot=slot)
    await db_session.commit()
    service = BookingService(db_session)

    # When
    found_booking, _ = await service.get_booking_with_timeslots_by_id(
        booking_id=booking.id, user_id=admin.id, is_admin=True
    )

    # Then
    assert found_booking.id == booking.id


@pytest.mark.asyncio
async def test__get_booking_with_timeslots_by_id__raises_not_found_for_other_user(db_session, faker):
    # Given
    owner = await create_user(db_session, faker)
    other = await create_user(db_session, faker)
    location = await create_location(db_session, faker)
    room = await create_room(db_session, faker, location=location)
    start = datetime.now(timezone.utc)
    slot = await create_timeslot(
        db_session,
        room=room,
        start_datetime=start,
        end_datetime=start + timedelta(hours=1),
    )
    booking = await create_booking(db_session, user=owner, room=room, timeslot=slot)
    await db_session.commit()
    service = BookingService(db_session)

    # When / Then
    with pytest.raises(NotFoundException):
        await service.get_booking_with_timeslots_by_id(
            booking_id=booking.id, user_id=other.id, is_admin=False
        )


@pytest.mark.asyncio
async def test__get_booking_with_timeslots_by_id__raises_not_found_for_missing(db_session):
    service = BookingService(db_session)

    with pytest.raises(NotFoundException):
        await service.get_booking_with_timeslots_by_id(
            booking_id=9999, user_id=1, is_admin=False
        )
