from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select

from app.models import Room, TimeSlot
from app.models.booking import BookingStatus
from app.models.timeslot import TimeSlotStatus
from app.schemas.room import SRoomCreate, SRoomUpdate
from app.schemas.timeslot import STimeSlotCreate, STimeSlotDateRange
from app.services.business.rooms import RoomBusinessService
from tests.fixtures.factories import (
    create_booking,
    create_location,
    create_room,
    create_timeslot,
    create_user,
)


@pytest.mark.asyncio
async def test__create_by_location_id__persists_room(db_session, faker):
    # Given
    location = await create_location(db_session, faker)
    await db_session.commit()
    service = RoomBusinessService()
    payload = SRoomCreate(
        name="Blue Room",
        capacity=8,
        description="Board room",
        is_active=True,
    )

    # When
    result = await service.create_by_location_id(location.id, payload)

    # Then
    assert result.name == payload.name
    stmt = select(Room).where(Room.id == result.id)
    stored = (await db_session.execute(stmt)).scalar_one()
    assert stored.location_id == location.id


@pytest.mark.asyncio
async def test__create_timeslot__saves_slot(db_session, faker):
    # Given
    location = await create_location(db_session, faker)
    room = await create_room(db_session, faker, location=location)
    await db_session.commit()
    service = RoomBusinessService()
    start = datetime.now(timezone.utc)
    slot_payload = STimeSlotCreate(
        start_datetime=start,
        end_datetime=start + timedelta(hours=2),
        base_price=100,
        status=TimeSlotStatus.AVAILABLE,
    )

    # When
    result = await service.create_timeslot(room_id=room.id, timeslot_data=slot_payload)

    # Then
    assert result.room_id == room.id
    stmt = select(TimeSlot).where(TimeSlot.id == result.id)
    stored = (await db_session.execute(stmt)).scalar_one()
    assert stored.start_datetime.replace(tzinfo=timezone.utc) == slot_payload.start_datetime


@pytest.mark.asyncio
async def test__get_timeslots_by_date_range_with_booking_flag__marks_active_bookings(db_session, faker):
    # Given
    user = await create_user(db_session, faker)
    location = await create_location(db_session, faker)
    room = await create_room(db_session, faker, location=location)
    start = datetime.now(timezone.utc)
    slot_with_booking = await create_timeslot(
        db_session,
        room=room,
        start_datetime=start,
        end_datetime=start + timedelta(hours=1),
    )
    slot_free = await create_timeslot(
        db_session,
        room=room,
        start_datetime=start + timedelta(hours=2),
        end_datetime=start + timedelta(hours=3),
    )
    await create_booking(
        db_session,
        user=user,
        room=room,
        timeslot=slot_with_booking,
        status=BookingStatus.PAID,
    )
    await db_session.commit()
    service = RoomBusinessService()
    date_range = STimeSlotDateRange(
        date_from=start - timedelta(minutes=5),
        date_to=slot_free.end_datetime + timedelta(minutes=5),
    )

    # When
    result = await service.get_timeslots_by_date_range_with_booking_flag(room.id, date_range)

    # Then
    assert len(result) == 2
    flag_map = {item.id: item.has_active_booking for item in result}
    assert flag_map[slot_with_booking.id] is True
    assert flag_map[slot_free.id] is False


@pytest.mark.asyncio
async def test__update_by_id__updates_selected_fields(db_session, faker):
    # Given
    location = await create_location(db_session, faker)
    room = await create_room(db_session, faker, location=location)
    await db_session.commit()
    service = RoomBusinessService()
    payload = SRoomUpdate(name="Renovated room", capacity=room.capacity + 5)

    # When
    result = await service.update_by_id(room.id, payload)

    # Then
    assert result.name == payload.name
    await db_session.refresh(room)
    assert room.name == payload.name
    assert room.capacity == payload.capacity


@pytest.mark.asyncio
async def test__delete_by_id__removes_room(db_session, faker):
    # Given
    location = await create_location(db_session, faker)
    room = await create_room(db_session, faker, location=location)
    await db_session.commit()
    service = RoomBusinessService()

    # When
    await service.delete_by_id(room.id)

    # Then
    result = (await db_session.execute(select(Room).where(Room.id == room.id))).scalar_one_or_none()
    assert result is None
