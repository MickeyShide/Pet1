from datetime import datetime, timedelta, timezone

import pytest

from app.models.booking import BookingStatus
from app.repositories.timeslot import TimeSlotRepository
from tests.fixtures.factories import (
    create_booking,
    create_location,
    create_room,
    create_timeslot,
    create_user,
)


@pytest.mark.asyncio
async def test__get_all_by_room_id_and_date_range__returns_only_matching_sorted_slots(db_session, faker):
    # Given
    location = await create_location(db_session, faker)
    room = await create_room(db_session, faker, location=location)
    other_room = await create_room(db_session, faker, location=location)
    start = datetime.now(timezone.utc)
    slot_before = await create_timeslot(
        db_session,
        room=room,
        start_datetime=start - timedelta(hours=3),
        end_datetime=start - timedelta(hours=2),
    )
    slot_overlap = await create_timeslot(
        db_session,
        room=room,
        start_datetime=start + timedelta(minutes=30),
        end_datetime=start + timedelta(hours=1),
    )
    slot_a = await create_timeslot(
        db_session,
        room=room,
        start_datetime=start + timedelta(hours=2),
        end_datetime=start + timedelta(hours=3),
    )
    slot_b = await create_timeslot(
        db_session,
        room=room,
        start_datetime=start + timedelta(hours=4),
        end_datetime=start + timedelta(hours=5),
    )
    slot_after = await create_timeslot(
        db_session,
        room=room,
        start_datetime=start + timedelta(hours=8),
        end_datetime=start + timedelta(hours=9),
    )
    await create_timeslot(
        db_session,
        room=other_room,
        start_datetime=start + timedelta(hours=1),
        end_datetime=start + timedelta(hours=2),
    )
    repo = TimeSlotRepository(db_session)
    date_from = start + timedelta(minutes=45)
    date_to = slot_b.end_datetime

    # When
    rows = await repo.get_all_by_room_id_and_date_range(
        room_id=room.id,
        date_from=date_from,
        date_to=date_to,
    )

    # Then
    returned_ids = [slot.id for slot, _ in rows]
    assert returned_ids == [slot_overlap.id, slot_a.id, slot_b.id]
    excluded_ids = {slot_before.id, slot_after.id}
    assert not excluded_ids.intersection(returned_ids)


@pytest.mark.asyncio
async def test__get_all_by_room_id_and_date_range__sets_booking_flags_by_status(db_session, faker):
    # Given
    user = await create_user(db_session, faker)
    location = await create_location(db_session, faker)
    room = await create_room(db_session, faker, location=location)
    start = datetime.now(timezone.utc)
    slot_taken = await create_timeslot(
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
    )
    slot_free = await create_timeslot(
        db_session,
        room=room,
        start_datetime=start + timedelta(hours=4),
        end_datetime=start + timedelta(hours=5),
    )
    await create_booking(
        db_session,
        user=user,
        room=room,
        timeslot=slot_taken,
        status=BookingStatus.PAID,
    )
    await create_booking(
        db_session,
        user=user,
        room=room,
        timeslot=slot_canceled,
        status=BookingStatus.CANCELED,
    )
    repo = TimeSlotRepository(db_session)

    # When
    rows = await repo.get_all_by_room_id_and_date_range(
        room_id=room.id,
        date_from=slot_taken.start_datetime,
        date_to=slot_free.end_datetime,
    )

    # Then
    flags = {slot.id: flag for slot, flag in rows}
    assert flags[slot_taken.id] is True
    assert flags[slot_canceled.id] is False
    assert flags[slot_free.id] is False


@pytest.mark.asyncio
async def test__get_all_by_room_id_and_date_range__includes_slot_ending_at_start(db_session, faker):
    location = await create_location(db_session, faker)
    room = await create_room(db_session, faker, location=location)
    start = datetime.now(timezone.utc)
    slot_ending_at_start = await create_timeslot(
        db_session,
        room=room,
        start_datetime=start - timedelta(hours=1),
        end_datetime=start,
    )
    slot_inside = await create_timeslot(
        db_session,
        room=room,
        start_datetime=start + timedelta(minutes=10),
        end_datetime=start + timedelta(minutes=40),
    )
    repo = TimeSlotRepository(db_session)

    rows = await repo.get_all_by_room_id_and_date_range(
        room_id=room.id,
        date_from=start,
        date_to=start + timedelta(hours=1, minutes=1),
    )

    returned_ids = [slot.id for slot, _ in rows]
    assert returned_ids == [slot_ending_at_start.id, slot_inside.id]


@pytest.mark.asyncio
async def test__get_all_by_room_id_and_date_range__includes_slot_starting_at_end(db_session, faker):
    location = await create_location(db_session, faker)
    room = await create_room(db_session, faker, location=location)
    start = datetime.now(timezone.utc)
    slot_inside = await create_timeslot(
        db_session,
        room=room,
        start_datetime=start + timedelta(minutes=10),
        end_datetime=start + timedelta(minutes=40),
    )
    slot_starting_at_end = await create_timeslot(
        db_session,
        room=room,
        start_datetime=start + timedelta(hours=1),
        end_datetime=start + timedelta(hours=2),
    )
    repo = TimeSlotRepository(db_session)

    rows = await repo.get_all_by_room_id_and_date_range(
        room_id=room.id,
        date_from=start,
        date_to=start + timedelta(hours=1),
    )

    returned_ids = [slot.id for slot, _ in rows]
    assert returned_ids == [slot_inside.id, slot_starting_at_end.id]


@pytest.mark.asyncio
async def test__get_all_by_room_id_and_date_range__includes_slot_covering_range(db_session, faker):
    location = await create_location(db_session, faker)
    room = await create_room(db_session, faker, location=location)
    start = datetime.now(timezone.utc)
    slot_cover = await create_timeslot(
        db_session,
        room=room,
        start_datetime=start - timedelta(hours=2),
        end_datetime=start + timedelta(hours=3),
    )
    repo = TimeSlotRepository(db_session)

    rows = await repo.get_all_by_room_id_and_date_range(
        room_id=room.id,
        date_from=start + timedelta(minutes=30),
        date_to=start + timedelta(hours=1),
    )

    returned_ids = [slot.id for slot, _ in rows]
    assert returned_ids == [slot_cover.id]
