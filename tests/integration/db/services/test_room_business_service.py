from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest
from sqlalchemy import select

from app.models import Room, TimeSlot
from app.models.booking import BookingStatus
from app.models.timeslot import TimeSlotStatus
from app.models.room import TimeSlotType
from app.schemas.room import SRoomCreate, SRoomUpdate
from app.schemas.timeslot import STimeSlotCreate, STimeSlotDateRange, STimeSlotOutWithBookingStatus
from app.services.business.rooms import RoomBusinessService
from app.services.business import rooms as rooms_module
from app.utils.err.room import NotFlexibleTimeslotsType, InvalidBookingDuration
from tests.factories import (
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
    await db_session.flush()
    service = RoomBusinessService()
    payload = SRoomCreate(
        name="Blue Room",
        capacity=8,
        description="Board room",
        is_active=True,
        time_slot_type=TimeSlotType.FLEXIBLE,
        hour_price=Decimal(150.0),
    )

    # When
    result = await service.create_by_location_id(location.id, payload)

    # Then
    assert result.name == payload.name
    stmt = select(Room).where(Room.id == result.id)
    stored = (await db_session.execute(stmt)).scalar_one()
    assert stored.location_id == location.id
    assert stored.hour_price == payload.hour_price
    assert stored.time_slot_type == payload.time_slot_type
    assert result.min_booking_duration_minutes == 60
    assert result.booking_step_minutes == 60
    assert stored.min_booking_duration_minutes == 60
    assert stored.booking_step_minutes == 60


@pytest.mark.asyncio
async def test__get_all_with_location__returns_location_data(db_session, faker):
    # Given
    location = await create_location(db_session, faker)
    room_a = await create_room(db_session, faker, location=location)
    room_b = await create_room(db_session, faker, location=location)
    await db_session.flush()
    service = RoomBusinessService()

    # When
    result = await service.get_all_with_location()

    # Then
    ids = {room.id for room in result}
    assert {room_a.id, room_b.id}.issubset(ids)
    for room in result:
        assert room.location.id == location.id


@pytest.mark.asyncio
async def test__get_all_with_location__empty(db_session):
    # Given
    service = RoomBusinessService()

    # When
    result = await service.get_all_with_location()

    # Then
    assert result == []


@pytest.mark.asyncio
async def test__create_timeslot__saves_slot(db_session, faker):
    # Given
    location = await create_location(db_session, faker)
    room = await create_room(db_session, faker, location=location)
    await db_session.flush()
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
    await db_session.flush()
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
async def test__get_timeslots_by_date_range_with_booking_flag__excludes_canceled_timeslots(db_session, faker):
    # Given
    location = await create_location(db_session, faker)
    room = await create_room(db_session, faker, location=location)
    start = datetime.now(timezone.utc)
    slot_available = await create_timeslot(
        db_session,
        room=room,
        start_datetime=start,
        end_datetime=start + timedelta(hours=1),
    )
    slot_canceled = await create_timeslot(
        db_session,
        room=room,
        start_datetime=start + timedelta(hours=2),
        end_datetime=start + timedelta(hours=3),
        status=TimeSlotStatus.CANCELED,
    )
    await db_session.flush()
    service = RoomBusinessService()
    date_range = STimeSlotDateRange(
        date_from=start - timedelta(minutes=5),
        date_to=slot_canceled.end_datetime + timedelta(minutes=5),
    )

    # When
    result = await service.get_timeslots_by_date_range_with_booking_flag(room.id, date_range)

    # Then
    ids = {item.id for item in result}
    assert slot_available.id in ids
    assert slot_canceled.id not in ids


@pytest.mark.asyncio
async def test__get_timeslots_by_date_range_with_booking_flag__uses_cache(monkeypatch, db_session, faker):
    # Given
    location = await create_location(db_session, faker)
    room = await create_room(db_session, faker, location=location)
    await db_session.flush()
    service = RoomBusinessService()
    start = datetime(2024, 1, 1, tzinfo=timezone.utc)
    end = start + timedelta(hours=1)
    cached = [
        STimeSlotOutWithBookingStatus(
            id=1,
            room_id=room.id,
            start_datetime=start,
            end_datetime=end,
            base_price=Decimal("100.00"),
            status=TimeSlotStatus.AVAILABLE,
            has_active_booking=False,
        )
    ]

    async def fake_try_get(self, key: str, default=None):
        return cached

    async def fake_try_set(self, key: str, value, ttl=None):
        raise AssertionError("should not populate cache when hit exists")

    class StubTimeslotService:
        async def get_all_by_room_id_and_date_range(self, *args, **kwargs):
            raise AssertionError("should not query timeslots when cache hit exists")

    monkeypatch.setattr(rooms_module.CacheService, "try_get", fake_try_get, raising=False)
    monkeypatch.setattr(rooms_module.CacheService, "try_set", fake_try_set, raising=False)
    service.timeslots_service = StubTimeslotService()

    # When
    result = await service.get_timeslots_by_date_range_with_booking_flag(
        room.id,
        STimeSlotDateRange(date_from=start, date_to=end),
    )

    # Then
    assert result == cached


@pytest.mark.asyncio
async def test__update_by_id__updates_selected_fields(db_session, faker):
    # Given
    location = await create_location(db_session, faker)
    room = await create_room(db_session, faker, location=location)
    await db_session.flush()
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
async def test__update_by_id__updates_new_fields(db_session, faker):
    # Given
    location = await create_location(db_session, faker)
    room = await create_room(db_session, faker, location=location, hour_price=50)
    await db_session.flush()
    service = RoomBusinessService()
    payload = SRoomUpdate(hour_price=250, time_slot_type=TimeSlotType.FIXED)

    # When
    result = await service.update_by_id(room.id, payload)

    # Then
    assert result.hour_price == payload.hour_price
    assert result.time_slot_type == payload.time_slot_type
    await db_session.refresh(room)
    assert room.hour_price == payload.hour_price
    assert room.time_slot_type == payload.time_slot_type


@pytest.mark.asyncio
async def test__update_by_id__updates_booking_duration_fields(db_session, faker):
    # Given
    location = await create_location(db_session, faker)
    room = await create_room(db_session, faker, location=location)
    await db_session.flush()
    service = RoomBusinessService()
    payload = SRoomUpdate(min_booking_duration_minutes=90, booking_step_minutes=30)

    # When
    result = await service.update_by_id(room.id, payload)

    # Then
    assert result.min_booking_duration_minutes == payload.min_booking_duration_minutes
    assert result.booking_step_minutes == payload.booking_step_minutes
    await db_session.refresh(room)
    assert room.min_booking_duration_minutes == payload.min_booking_duration_minutes
    assert room.booking_step_minutes == payload.booking_step_minutes


@pytest.mark.asyncio
async def test__delete_by_id__removes_room(db_session, faker):
    # Given
    location = await create_location(db_session, faker)
    room = await create_room(db_session, faker, location=location)
    await db_session.flush()
    service = RoomBusinessService()

    # When
    await service.delete_by_id(room.id)

    # Then
    result = (await db_session.execute(select(Room).where(Room.id == room.id))).scalar_one_or_none()
    assert result is None


@pytest.mark.asyncio
async def test__get_price_quote__flexible_returns_price(db_session, faker):
    # Given
    location = await create_location(db_session, faker)
    room = await create_room(
        db_session,
        faker,
        location=location,
        hour_price=150,
        time_slot_type=TimeSlotType.FLEXIBLE,
    )
    await db_session.flush()
    service = RoomBusinessService()
    start = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
    end = start + timedelta(hours=2)

    # When
    result = await service.get_price_quote(room.id, start, end)

    # Then
    assert result.price == Decimal("300.00")


@pytest.mark.asyncio
async def test__get_price_quote__fixed_raises_conflict(db_session, faker):
    # Given
    location = await create_location(db_session, faker)
    room = await create_room(
        db_session,
        faker,
        location=location,
        time_slot_type=TimeSlotType.FIXED,
    )
    await db_session.flush()
    service = RoomBusinessService()
    start = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
    end = start + timedelta(hours=1)

    # When / Then
    with pytest.raises(NotFlexibleTimeslotsType):
        await service.get_price_quote(room.id, start, end)


@pytest.mark.asyncio
async def test__get_price_quote__rejects_too_short_duration(db_session, faker):
    # Given
    location = await create_location(db_session, faker)
    room = await create_room(
        db_session,
        faker,
        location=location,
        hour_price=Decimal("100.00"),
        min_booking_duration_minutes=120,
        booking_step_minutes=30,
    )
    await db_session.flush()
    service = RoomBusinessService()
    start = datetime(2024, 1, 1, 10, 0, tzinfo=timezone.utc)
    end = start + timedelta(minutes=60)

    # When / Then
    with pytest.raises(InvalidBookingDuration):
        await service.get_price_quote(room.id, start, end)


@pytest.mark.asyncio
async def test__get_price_quote__rejects_unaligned_start(db_session, faker):
    # Given
    location = await create_location(db_session, faker)
    room = await create_room(
        db_session,
        faker,
        location=location,
        hour_price=Decimal("100.00"),
        min_booking_duration_minutes=60,
        booking_step_minutes=30,
    )
    await db_session.flush()
    service = RoomBusinessService()
    start = datetime(2024, 1, 1, 10, 10, tzinfo=timezone.utc)
    end = start + timedelta(hours=1)

    # When / Then
    with pytest.raises(InvalidBookingDuration):
        await service.get_price_quote(room.id, start, end)


@pytest.mark.asyncio
async def test__get_price_quote__rejects_unaligned_duration(db_session, faker):
    # Given
    location = await create_location(db_session, faker)
    room = await create_room(
        db_session,
        faker,
        location=location,
        hour_price=Decimal("100.00"),
        min_booking_duration_minutes=60,
        booking_step_minutes=30,
    )
    await db_session.flush()
    service = RoomBusinessService()
    start = datetime(2024, 1, 1, 10, 0, tzinfo=timezone.utc)
    end = start + timedelta(minutes=45)

    # When / Then
    with pytest.raises(InvalidBookingDuration):
        await service.get_price_quote(room.id, start, end)


@pytest.mark.asyncio
async def test__get_price_quote__rejects_seconds(db_session, faker):
    # Given
    location = await create_location(db_session, faker)
    room = await create_room(
        db_session,
        faker,
        location=location,
        hour_price=Decimal("100.00"),
        min_booking_duration_minutes=60,
        booking_step_minutes=30,
    )
    await db_session.flush()
    service = RoomBusinessService()
    start = datetime(2024, 1, 1, 10, 0, 30, tzinfo=timezone.utc)
    end = start + timedelta(hours=1)

    # When / Then
    with pytest.raises(InvalidBookingDuration):
        await service.get_price_quote(room.id, start, end)


@pytest.mark.asyncio
async def test__get_price_quote__allows_step_over_hour(db_session, faker):
    # Given
    location = await create_location(db_session, faker)
    room = await create_room(
        db_session,
        faker,
        location=location,
        hour_price=Decimal("100.00"),
        min_booking_duration_minutes=90,
        booking_step_minutes=90,
    )
    await db_session.flush()
    service = RoomBusinessService()
    start = datetime(2024, 1, 1, 1, 30, tzinfo=timezone.utc)
    end = start + timedelta(minutes=90)

    # When
    result = await service.get_price_quote(room.id, start, end)

    # Then
    assert result.price == Decimal("150.00")
