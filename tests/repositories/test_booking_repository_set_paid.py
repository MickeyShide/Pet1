from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy.exc import NoResultFound

from app.models.booking import BookingStatus
from app.repositories.booking import BookingRepository
from tests.fixtures.factories import (
    create_booking,
    create_location,
    create_room,
    create_timeslot,
    create_user,
)


@pytest.mark.asyncio
async def test__set_booking_paid__updates_pending_when_not_expired(db_session, faker):
    # Given
    user = await create_user(db_session, faker)
    location = await create_location(db_session, faker)
    room = await create_room(db_session, faker, location=location)
    start = datetime.now(timezone.utc) - timedelta(days=1)
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
        expires_delta=timedelta(hours=1),
    )
    await db_session.commit()
    repo = BookingRepository(db_session)

    # When
    updated = await repo.set_booking_paid(booking_id=booking.id)

    # Then
    assert updated.status == BookingStatus.PAID
    assert updated.paid_at is not None


@pytest.mark.asyncio
async def test__set_booking_paid__raises_for_not_pending(db_session, faker):
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
    repo = BookingRepository(db_session)

    # When / Then
    with pytest.raises(NoResultFound):
        await repo.set_booking_paid(booking_id=booking.id)


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
    repo = BookingRepository(db_session)

    # When / Then
    with pytest.raises(NoResultFound):
        await repo.set_booking_paid(booking_id=booking.id)
