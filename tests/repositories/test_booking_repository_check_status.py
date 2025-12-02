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
async def test__check_booking_status__returns_status_for_owner(db_session, faker):
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
    booking = await create_booking(db_session, user=user, room=room, timeslot=slot, status=BookingStatus.PAID)
    await db_session.commit()
    repo = BookingRepository(db_session)

    # When
    status = await repo.check_booking_status(booking_id=booking.id, user_id=user.id, is_admin=False)

    # Then
    assert status == BookingStatus.PAID


@pytest.mark.asyncio
async def test__check_booking_status__admin_can_check_other_user(db_session, faker):
    # Given
    owner = await create_user(db_session, faker)
    admin = await create_user(db_session, faker)
    location = await create_location(db_session, faker)
    room = await create_room(db_session, faker, location=location)
    start = datetime.now(timezone.utc)
    slot = await create_timeslot(
        db_session,
        room=room,
        start_datetime=start,
        end_datetime=start + timedelta(hours=1),
    )
    booking = await create_booking(db_session, user=owner, room=room, timeslot=slot, status=BookingStatus.PENDING_PAYMENTS)
    await db_session.commit()
    repo = BookingRepository(db_session)

    # When
    status = await repo.check_booking_status(booking_id=booking.id, user_id=admin.id, is_admin=True)

    # Then
    assert status == BookingStatus.PENDING_PAYMENTS


@pytest.mark.asyncio
async def test__check_booking_status__raises_for_other_user(db_session, faker):
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
    booking = await create_booking(db_session, user=owner, room=room, timeslot=slot, status=BookingStatus.PAID)
    await db_session.commit()
    repo = BookingRepository(db_session)

    # When / Then
    with pytest.raises(NoResultFound):
        await repo.check_booking_status(booking_id=booking.id, user_id=other.id, is_admin=False)


@pytest.mark.asyncio
async def test__check_booking_status__raises_for_missing(db_session):
    repo = BookingRepository(db_session)
    with pytest.raises(NoResultFound):
        await repo.check_booking_status(booking_id=9999, user_id=1, is_admin=False)
