from datetime import datetime, timedelta, timezone

import pytest

from app.models import Booking
from app.schemas.auth import SAccessToken
from app.schemas.booking import SBookingCreate
from app.services.business.bookings import BookingsBusinessService
from app.utils.err.booking import SlotAlreadyTaken
from tests.fixtures.factories import (
    create_booking,
    create_location,
    create_room,
    create_timeslot,
    create_user,
)
from sqlalchemy import select
from app.models.booking import BookingStatus


@pytest.mark.asyncio
async def test__create_booking__persists_new_booking(db_session, faker):
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
    await db_session.commit()
    service = BookingsBusinessService(token_data=SAccessToken(sub=str(user.id), admin=False))
    payload = SBookingCreate(timeslot_id=slot.id)

    # When
    result = await service.create_booking(payload)

    # Then
    assert result.timeslot_id == slot.id
    stmt = select(Booking).where(Booking.id == result.id)
    stored = (await db_session.execute(stmt)).scalar_one()
    assert stored.user_id == user.id
    assert stored.status == BookingStatus.PENDING_PAYMENTS


@pytest.mark.asyncio
async def test__create_booking__raises_when_slot_already_taken(db_session, faker):
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
    await db_session.commit()
    service = BookingsBusinessService(token_data=SAccessToken(sub=str(user.id), admin=False))

    # When / Then
    with pytest.raises(SlotAlreadyTaken):
        await service.create_booking(SBookingCreate(timeslot_id=slot.id))
