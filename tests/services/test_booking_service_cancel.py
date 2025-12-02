from datetime import datetime, timedelta, timezone

import pytest

from app.models.booking import BookingStatus
from app.services.booking import BookingService
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
async def test__cancel_booking__returns_true_for_owner_pending(db_session, faker):
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
    booking = await create_booking(
        db_session,
        user=user,
        room=room,
        timeslot=slot,
        status=BookingStatus.PENDING_PAYMENTS,
    )
    await db_session.commit()
    service = BookingService(db_session)

    # When
    result = await service.cancel_booking(booking_id=booking.id, user_id=user.id, is_admin=False)

    # Then
    assert result is True
    await db_session.refresh(booking)
    assert booking.status == BookingStatus.CANCELED


@pytest.mark.asyncio
async def test__cancel_booking__admin_can_cancel_other_users(db_session, faker):
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
    booking = await create_booking(
        db_session,
        user=other,
        room=room,
        timeslot=slot,
        status=BookingStatus.PENDING_PAYMENTS,
    )
    await db_session.commit()
    service = BookingService(db_session)

    # When
    result = await service.cancel_booking(booking_id=booking.id, user_id=admin.id, is_admin=True)

    # Then
    assert result is True
    await db_session.refresh(booking)
    assert booking.status == BookingStatus.CANCELED


@pytest.mark.asyncio
async def test__cancel_booking__raises_not_found_for_other_user(db_session, faker):
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
    booking = await create_booking(
        db_session,
        user=other,
        room=room,
        timeslot=slot,
        status=BookingStatus.PENDING_PAYMENTS,
    )
    await db_session.commit()
    service = BookingService(db_session)

    # When / Then
    with pytest.raises(NotFoundException):
        await service.cancel_booking(booking_id=booking.id, user_id=owner.id, is_admin=False)


@pytest.mark.asyncio
async def test__cancel_booking__raises_not_found_for_missing_booking(db_session):
    # Given
    service = BookingService(db_session)

    # When / Then
    with pytest.raises(NotFoundException):
        await service.cancel_booking(booking_id=9999, user_id=1, is_admin=False)


@pytest.mark.asyncio
async def test__cancel_booking__returns_false_if_not_pending(db_session, faker):
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
    booking = await create_booking(
        db_session,
        user=user,
        room=room,
        timeslot=slot,
        status=BookingStatus.CANCELED,
    )
    await db_session.commit()
    service = BookingService(db_session)

    # When
    with pytest.raises(ConflictException):  # 409 already cancelled
        await service.cancel_booking(booking_id=booking.id, user_id=user.id, is_admin=False)


@pytest.mark.asyncio
async def test__cancel_booking__sets_canceled_timestamp(db_session, faker):
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
    booking = await create_booking(
        db_session,
        user=user,
        room=room,
        timeslot=slot,
        status=BookingStatus.PENDING_PAYMENTS,
    )
    await db_session.commit()
    service = BookingService(db_session)

    # When
    await service.cancel_booking(booking_id=booking.id, user_id=user.id, is_admin=False)

    # Then
    await db_session.refresh(booking)
    # ❗BUG FOUND: canceled_at stays None after cancel; expected timestamp set when booking is canceled.
    assert booking.canceled_at is not None
