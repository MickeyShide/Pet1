from datetime import datetime, timedelta, timezone

import pytest

from app.models.booking import BookingStatus
from app.schemas.auth import SAccessToken
from app.services.business.bookings import BookingsBusinessService
from app.utils.err.base.conflict import ConflictException
from app.utils.err.base.not_found import NotFoundException
from tests.fixtures.factories import (
    create_booking,
    create_location,
    create_room,
    create_timeslot,
    create_user,
)


@pytest.mark.asyncio
async def test__cancel_booking_business__owner_cancels_pending(db_session, faker):
    # Given a pending booking owned by the user
    user = await create_user(db_session, faker)
    token = SAccessToken(sub=str(user.id), admin=False)
    location = await create_location(db_session, faker)
    room = await create_room(db_session, faker, location=location)
    start = datetime.now(timezone.utc)
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
    )
    await db_session.commit()
    service = BookingsBusinessService(token_data=token)

    # When the owner cancels the booking
    result = await service.cancel_booking(booking.id)

    # Then the booking is marked canceled
    assert result is True
    await db_session.refresh(booking)
    assert booking.status == BookingStatus.CANCELED


@pytest.mark.asyncio
async def test__cancel_booking_business__raises_not_found_for_other_user(db_session, faker):
    # Given a booking owned by someone else
    owner = await create_user(db_session, faker)
    other = await create_user(db_session, faker)
    token = SAccessToken(sub=str(other.id), admin=False)
    location = await create_location(db_session, faker)
    room = await create_room(db_session, faker, location=location)
    start = datetime.now(timezone.utc)
    slot = await create_timeslot(
        db_session,
        room=room,
        start_datetime=start,
        end_datetime=start + timedelta(hours=1),
    )
    booking = await create_booking(
        db_session,
        user=owner,
        room=room,
        timeslot=slot,
        status=BookingStatus.PENDING_PAYMENTS,
    )
    await db_session.commit()
    service = BookingsBusinessService(token_data=token)

    # When / Then a non-owner cannot cancel it
    with pytest.raises(NotFoundException):
        await service.cancel_booking(booking.id)


@pytest.mark.asyncio
async def test__cancel_booking_business__raises_conflict_for_not_pending(db_session, faker):
    # Given a paid booking
    user = await create_user(db_session, faker)
    token = SAccessToken(sub=str(user.id), admin=False)
    location = await create_location(db_session, faker)
    room = await create_room(db_session, faker, location=location)
    start = datetime.now(timezone.utc)
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
        status=BookingStatus.PAID,
    )
    await db_session.commit()
    service = BookingsBusinessService(token_data=token)

    # When / Then cancel returns conflict for non-pending status
    with pytest.raises(ConflictException):
        await service.cancel_booking(booking.id)
