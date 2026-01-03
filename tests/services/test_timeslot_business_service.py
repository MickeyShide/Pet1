from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select

from app.models import TimeSlot
from app.schemas.timeslot import STimeSlotUpdate
from app.services.business.timeslots import TimeSlotBusinessService
from tests.fixtures.factories import (
    create_location,
    create_room,
    create_timeslot,
)


@pytest.mark.asyncio
async def test__update_timeslot_by_id__applies_partial_fields(db_session, faker):
    # Given
    location = await create_location(db_session, faker)
    room = await create_room(db_session, faker, location=location)
    start = datetime.now(timezone.utc)
    slot = await create_timeslot(
        db_session,
        room=room,
        start_datetime=start,
        end_datetime=start + timedelta(hours=1),
        base_price=200,
    )
    await db_session.commit()
    service = TimeSlotBusinessService()
    payload = STimeSlotUpdate(base_price=350)

    # When
    updated = await service.update_timeslot_by_id(slot.id, payload)

    # Then
    assert isinstance(updated, TimeSlot)
    assert updated.base_price == payload.base_price
    await db_session.refresh(slot)
    assert slot.base_price == payload.base_price


@pytest.mark.asyncio
async def test__delete_timeslot_by_id__removes_slot(db_session, faker):
    # Given
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
    service = TimeSlotBusinessService()

    # When
    await service.delete_timeslot_by_id(slot.id)

    # Then
    result = (await db_session.execute(select(TimeSlot).where(TimeSlot.id == slot.id))).scalar_one_or_none()
    assert result is None


@pytest.mark.asyncio
async def test__get_by_room_and_date_range__returns_label_and_hours(db_session, faker):
    location = await create_location(db_session, faker)
    room = await create_room(db_session, faker, location=location)
    start = datetime(2025, 1, 1, 9, 5, tzinfo=timezone.utc)
    end = start + timedelta(hours=1, minutes=30)
    slot = await create_timeslot(
        db_session,
        room=room,
        start_datetime=start,
        end_datetime=end,
    )
    await db_session.commit()
    service = TimeSlotBusinessService()

    result = await service.get_by_room_and_date_range(
        room_id=room.id,
        date_from=start - timedelta(minutes=1),
        date_to=end + timedelta(minutes=1),
    )

    assert len(result) == 1
    item = result[0]
    assert item.id == str(slot.id)
    assert item.date_from == start
    assert item.date_to == end
    assert item.label == "09:05 - 10:35"
    assert item.hours == pytest.approx(1.5)


@pytest.mark.asyncio
async def test__get_by_room_and_date_range__filters_by_room(db_session, faker):
    location = await create_location(db_session, faker)
    room_a = await create_room(db_session, faker, location=location)
    room_b = await create_room(db_session, faker, location=location)
    start = datetime.now(timezone.utc)
    await create_timeslot(
        db_session,
        room=room_a,
        start_datetime=start,
        end_datetime=start + timedelta(hours=1),
    )
    await create_timeslot(
        db_session,
        room=room_b,
        start_datetime=start,
        end_datetime=start + timedelta(hours=1),
    )
    await db_session.commit()
    service = TimeSlotBusinessService()

    result = await service.get_by_room_and_date_range(
        room_id=room_a.id,
        date_from=start - timedelta(minutes=1),
        date_to=start + timedelta(hours=2),
    )

    assert len(result) == 1
    assert result[0].id is not None


@pytest.mark.asyncio
async def test__get_by_room_and_date_range__returns_empty_when_no_matches(db_session, faker):
    location = await create_location(db_session, faker)
    room = await create_room(db_session, faker, location=location)
    start = datetime.now(timezone.utc)
    await create_timeslot(
        db_session,
        room=room,
        start_datetime=start,
        end_datetime=start + timedelta(hours=1),
    )
    await db_session.commit()
    service = TimeSlotBusinessService()

    result = await service.get_by_room_and_date_range(
        room_id=room.id,
        date_from=start + timedelta(hours=2),
        date_to=start + timedelta(hours=3),
    )

    assert result == []
