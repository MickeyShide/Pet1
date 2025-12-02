from datetime import datetime, timedelta, timezone

import pytest

from app.schemas.auth import SAccessToken
from app.services.business.bookings import BookingsBusinessService
from app.utils.err.base.not_found import NotFoundException
from tests.fixtures.factories import (
    create_booking,
    create_location,
    create_room,
    create_timeslot,
    create_user,
)


@pytest.mark.asyncio
async def test__get_booking_by_id_business__returns_for_owner(db_session, faker):
    # Given
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
    booking = await create_booking(db_session, user=user, room=room, timeslot=slot)
    await db_session.commit()
    service = BookingsBusinessService(token_data=token)

    # When
    result = await service.get_booking_by_id(booking.id)

    # Then
    assert result.booking.id == booking.id
    assert result.timeslot.id == slot.id


@pytest.mark.asyncio
async def test__get_booking_by_id_business__admin_can_view_other(db_session, faker):
    # Given
    admin = await create_user(db_session, faker)
    admin_token = SAccessToken(sub=str(admin.id), admin=True)
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
    service = BookingsBusinessService(token_data=admin_token)

    # When
    result = await service.get_booking_by_id(booking.id)

    # Then
    assert result.booking.id == booking.id


@pytest.mark.asyncio
async def test__get_booking_by_id_business__raises_for_other_user(db_session, faker):
    # Given
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
    booking = await create_booking(db_session, user=owner, room=room, timeslot=slot)
    await db_session.commit()
    service = BookingsBusinessService(token_data=token)

    # When / Then
    with pytest.raises(NotFoundException):
        await service.get_booking_by_id(booking.id)
