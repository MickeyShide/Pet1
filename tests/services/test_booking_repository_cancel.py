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
async def test__cancel_booking_repo__owner_cancels_pending(db_session, faker):
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
    repo = BookingRepository(db_session)

    # When
    canceled = await repo.cancel_booking(
        booking_id=booking.id,
        user_id=user.id,
        is_admin=False,
    )

    # Then
    assert canceled.status == BookingStatus.CANCELED


@pytest.mark.asyncio
async def test__cancel_booking_repo__admin_cancels_other_user(db_session, faker):
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
    repo = BookingRepository(db_session)

    # When
    canceled = await repo.cancel_booking(
        booking_id=booking.id,
        user_id=admin.id,
        is_admin=True,
    )

    # Then
    assert canceled.status == BookingStatus.CANCELED


@pytest.mark.asyncio
async def test__cancel_booking_repo__raises_for_other_user(db_session, faker):
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
        user=owner,
        room=room,
        timeslot=slot,
        status=BookingStatus.PENDING_PAYMENTS,
    )
    await db_session.commit()
    repo = BookingRepository(db_session)

    # When / Then
    with pytest.raises(NoResultFound):
        await repo.cancel_booking(
            booking_id=booking.id,
            user_id=other.id,
            is_admin=False,
        )


@pytest.mark.asyncio
async def test__cancel_booking_repo__raises_for_not_pending(db_session, faker):
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
        status=BookingStatus.PAID,
    )
    await db_session.commit()
    repo = BookingRepository(db_session)

    # When / Then
    with pytest.raises(NoResultFound):
        await repo.cancel_booking(
            booking_id=booking.id,
            user_id=user.id,
            is_admin=False,
        )


@pytest.mark.asyncio
async def test__cancel_booking_repo__raises_for_missing(db_session):
    repo = BookingRepository(db_session)
    with pytest.raises(NoResultFound):
        await repo.cancel_booking(
            booking_id=9999,
            user_id=1,
            is_admin=False,
        )
