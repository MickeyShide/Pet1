from datetime import datetime, timedelta, timezone

import pytest

from app.models.booking import BookingStatus
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
async def test__set_booking_paid__marks_pending_when_not_expired(db_session, faker):
    # Given
    user = await create_user(db_session, faker)
    location = await create_location(db_session, faker)
    room = await create_room(db_session, faker, location=location)
    start = datetime.now(timezone.utc) + timedelta(hours=1)
    slot = await create_timeslot(
        db_session,
        room=room,
        start_datetime=start,
        end_datetime=start + timedelta(hours=1),
    )
    booking = await create_booking(
        db_session,
        user=user,
        room=room,
        timeslot=slot,
        status=BookingStatus.PENDING_PAYMENTS,
        expires_delta=timedelta(hours=2),
    )
    await db_session.commit()
    service = BookingService(db_session)

    # When
    updated = await service.set_booking_paid(booking.id)

    # Then
    assert updated.status == BookingStatus.PAID
    assert updated.paid_at is not None


@pytest.mark.asyncio
async def test__set_booking_paid__raises_for_expired_booking(db_session, faker):
    # Given
    user = await create_user(db_session, faker)
    location = await create_location(db_session, faker)
    room = await create_room(db_session, faker, location=location)
    start = datetime.now(timezone.utc) - timedelta(hours=2)
    slot = await create_timeslot(
        db_session,
        room=room,
        start_datetime=start,
        end_datetime=start + timedelta(hours=1),
    )
    booking = await create_booking(
        db_session,
        user=user,
        room=room,
        timeslot=slot,
        status=BookingStatus.PENDING_PAYMENTS,
        expires_delta=timedelta(hours=-1),
    )
    await db_session.commit()
    service = BookingService(db_session)

    # When / Then
    with pytest.raises(NotFoundException):  # should not allow paying expired bookings
        await service.set_booking_paid(booking.id)


@pytest.mark.asyncio
async def test__set_booking_paid__raises_for_non_pending(db_session, faker):
    # Given
    user = await create_user(db_session, faker)
    location = await create_location(db_session, faker)
    room = await create_room(db_session, faker, location=location)
    start = datetime.now(timezone.utc) + timedelta(hours=1)
    slot = await create_timeslot(
        db_session,
        room=room,
        start_datetime=start,
        end_datetime=start + timedelta(hours=1),
    )
    booking = await create_booking(
        db_session,
        user=user,
        room=room,
        timeslot=slot,
        status=BookingStatus.CANCELED,
    )
    await db_session.commit()
    service = BookingService(db_session)

    # When / Then
    with pytest.raises(NotFoundException):
        await service.set_booking_paid(booking.id)
