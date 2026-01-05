from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest
from sqlalchemy import select

from app.models import Booking, TimeSlot
from app.models.booking import BookingStatus
from app.models.room import TimeSlotType
from app.models.timeslot import TimeSlotStatus
from app.schemas.auth import SAccessToken
from app.schemas.booking import SBookingCreateFlexible
from app.services.business.bookings import BookingsBusinessService
from app.utils.err.base.not_found import NotFoundException
from app.utils.err.room import InvalidBookingDuration, NotFlexibleTimeslotsType
from app.utils.err.timeslot import InvalidTimeSlot
from tests.fixtures.factories import (
    create_location,
    create_room,
    create_timeslot,
    create_user,
)


@pytest.mark.asyncio
async def test__create_booking_flexible__persists_booking_and_timeslot(db_session, faker):
    user = await create_user(db_session, faker)
    location = await create_location(db_session, faker)
    room = await create_room(
        db_session,
        faker,
        location=location,
        hour_price=Decimal("200.00"),
        time_slot_type=TimeSlotType.FLEXIBLE,
        min_booking_duration_minutes=60,
        booking_step_minutes=30,
    )
    start = datetime(2024, 1, 1, 10, 0, tzinfo=timezone.utc)
    end = start + timedelta(minutes=90)
    await db_session.commit()

    service = BookingsBusinessService(token_data=SAccessToken(sub=str(user.id), admin=False))
    result = await service.create_booking_flexible(
        SBookingCreateFlexible(room_id=room.id, start_datetime=start, end_datetime=end)
    )

    expected_price = Decimal("300.00")
    assert result.booking.user_id == user.id
    assert result.booking.room.id == room.id
    assert result.booking.status == BookingStatus.PENDING_PAYMENTS
    assert result.booking.total_price == expected_price
    assert result.timeslot.room_id == room.id
    assert result.timeslot.start_datetime == start
    assert result.timeslot.end_datetime == end
    assert result.timeslot.status == TimeSlotStatus.AVAILABLE
    assert result.timeslot.base_price == expected_price

    stored_booking = (await db_session.execute(select(Booking).where(Booking.id == result.booking.id))).scalar_one()
    stored_timeslot = (await db_session.execute(select(TimeSlot).where(TimeSlot.id == result.timeslot.id))).scalar_one()
    assert stored_booking.user_id == user.id
    assert stored_booking.timeslot_id == stored_timeslot.id


@pytest.mark.asyncio
async def test__create_booking_flexible__raises_when_room_missing(db_session, faker):
    user = await create_user(db_session, faker)
    await db_session.commit()

    service = BookingsBusinessService(token_data=SAccessToken(sub=str(user.id), admin=False))
    start = datetime(2024, 1, 1, 10, 0, tzinfo=timezone.utc)
    end = start + timedelta(hours=1)

    with pytest.raises(NotFoundException):
        await service.create_booking_flexible(
            SBookingCreateFlexible(room_id=9999, start_datetime=start, end_datetime=end)
        )


@pytest.mark.asyncio
async def test__create_booking_flexible__rejects_fixed_room(db_session, faker):
    user = await create_user(db_session, faker)
    location = await create_location(db_session, faker)
    room = await create_room(
        db_session,
        faker,
        location=location,
        time_slot_type=TimeSlotType.FIXED,
        min_booking_duration_minutes=60,
        booking_step_minutes=30,
    )
    await db_session.commit()

    service = BookingsBusinessService(token_data=SAccessToken(sub=str(user.id), admin=False))
    start = datetime(2024, 1, 1, 10, 0, tzinfo=timezone.utc)
    end = start + timedelta(hours=1)

    with pytest.raises(NotFlexibleTimeslotsType):
        await service.create_booking_flexible(
            SBookingCreateFlexible(room_id=room.id, start_datetime=start, end_datetime=end)
        )


@pytest.mark.asyncio
async def test__create_booking_flexible__rejects_too_short_duration(db_session, faker):
    user = await create_user(db_session, faker)
    location = await create_location(db_session, faker)
    room = await create_room(
        db_session,
        faker,
        location=location,
        min_booking_duration_minutes=120,
        booking_step_minutes=30,
    )
    await db_session.commit()

    service = BookingsBusinessService(token_data=SAccessToken(sub=str(user.id), admin=False))
    start = datetime(2024, 1, 1, 10, 0, tzinfo=timezone.utc)
    end = start + timedelta(minutes=60)

    with pytest.raises(InvalidBookingDuration):
        await service.create_booking_flexible(
            SBookingCreateFlexible(room_id=room.id, start_datetime=start, end_datetime=end)
        )


@pytest.mark.asyncio
async def test__create_booking_flexible__rejects_unaligned_start(db_session, faker):
    user = await create_user(db_session, faker)
    location = await create_location(db_session, faker)
    room = await create_room(
        db_session,
        faker,
        location=location,
        min_booking_duration_minutes=60,
        booking_step_minutes=30,
    )
    await db_session.commit()

    service = BookingsBusinessService(token_data=SAccessToken(sub=str(user.id), admin=False))
    start = datetime(2024, 1, 1, 10, 10, tzinfo=timezone.utc)
    end = start + timedelta(hours=1)

    with pytest.raises(InvalidBookingDuration):
        await service.create_booking_flexible(
            SBookingCreateFlexible(room_id=room.id, start_datetime=start, end_datetime=end)
        )


@pytest.mark.asyncio
async def test__create_booking_flexible__rejects_unaligned_duration(db_session, faker):
    user = await create_user(db_session, faker)
    location = await create_location(db_session, faker)
    room = await create_room(
        db_session,
        faker,
        location=location,
        min_booking_duration_minutes=60,
        booking_step_minutes=30,
    )
    await db_session.commit()

    service = BookingsBusinessService(token_data=SAccessToken(sub=str(user.id), admin=False))
    start = datetime(2024, 1, 1, 10, 0, tzinfo=timezone.utc)
    end = start + timedelta(minutes=45)

    with pytest.raises(InvalidBookingDuration):
        await service.create_booking_flexible(
            SBookingCreateFlexible(room_id=room.id, start_datetime=start, end_datetime=end)
        )


@pytest.mark.asyncio
async def test__create_booking_flexible__rejects_seconds(db_session, faker):
    user = await create_user(db_session, faker)
    location = await create_location(db_session, faker)
    room = await create_room(
        db_session,
        faker,
        location=location,
        min_booking_duration_minutes=60,
        booking_step_minutes=30,
    )
    await db_session.commit()

    service = BookingsBusinessService(token_data=SAccessToken(sub=str(user.id), admin=False))
    start = datetime(2024, 1, 1, 10, 0, 30, tzinfo=timezone.utc)
    end = start + timedelta(hours=1)

    with pytest.raises(InvalidBookingDuration):
        await service.create_booking_flexible(
            SBookingCreateFlexible(room_id=room.id, start_datetime=start, end_datetime=end)
        )


@pytest.mark.asyncio
async def test__create_booking_flexible__rejects_end_before_start(db_session, faker):
    user = await create_user(db_session, faker)
    location = await create_location(db_session, faker)
    room = await create_room(
        db_session,
        faker,
        location=location,
        min_booking_duration_minutes=60,
        booking_step_minutes=30,
    )
    await db_session.commit()

    service = BookingsBusinessService(token_data=SAccessToken(sub=str(user.id), admin=False))
    start = datetime(2024, 1, 1, 11, 0, tzinfo=timezone.utc)
    end = datetime(2024, 1, 1, 10, 0, tzinfo=timezone.utc)

    with pytest.raises(InvalidBookingDuration):
        await service.create_booking_flexible(
            SBookingCreateFlexible(room_id=room.id, start_datetime=start, end_datetime=end)
        )


@pytest.mark.asyncio
async def test__create_booking_flexible__rejects_overlapping_timeslot(db_session, faker):
    user = await create_user(db_session, faker)
    location = await create_location(db_session, faker)
    room = await create_room(
        db_session,
        faker,
        location=location,
        min_booking_duration_minutes=30,
        booking_step_minutes=30,
    )
    start = datetime(2024, 1, 1, 10, 0, tzinfo=timezone.utc)
    end = start + timedelta(hours=1)
    await create_timeslot(
        db_session,
        room=room,
        start_datetime=start,
        end_datetime=end,
    )
    await db_session.commit()

    service = BookingsBusinessService(token_data=SAccessToken(sub=str(user.id), admin=False))
    overlap_start = start + timedelta(minutes=30)
    overlap_end = overlap_start + timedelta(hours=1)

    with pytest.raises(InvalidTimeSlot):
        await service.create_booking_flexible(
            SBookingCreateFlexible(
                room_id=room.id,
                start_datetime=overlap_start,
                end_datetime=overlap_end,
            )
        )
