from datetime import datetime, timedelta, timezone

import pytest

from app.celery_app import tasks
from app.models.room import TimeSlotType
from app.models.timeslot import TimeSlotStatus
from tests.factories import (
    create_booking,
    create_location,
    create_room,
    create_timeslot,
    create_user,
)

pytestmark = pytest.mark.db_commit


@pytest.mark.asyncio
async def test_expire_booking_skipped_when_not_expired(db_session, session_maker, faker, monkeypatch):
    monkeypatch.setattr(tasks, "async_session_maker", session_maker, raising=False)
    user = await create_user(db_session, faker)
    location = await create_location(db_session, faker)
    room = await create_room(db_session, faker, location=location)
    timeslot = await create_timeslot(
        db_session,
        room=room,
        start_datetime=datetime.now(timezone.utc),
        end_datetime=datetime.now(timezone.utc) + timedelta(hours=1),
    )
    booking = await create_booking(
        db_session,
        user=user,
        room=room,
        timeslot=timeslot,
        expires_delta=timedelta(minutes=30),
    )
    await db_session.commit()

    result = await tasks._expire_booking(booking.id)
    assert result["status"] == "skipped_not_pending_or_not_expired"


@pytest.mark.asyncio
async def test_expire_booking_expires_and_invalidates_cache(db_session, session_maker, faker, monkeypatch):
    deleted_patterns: list[str] = []

    async def fake_delete_pattern(self, pattern: str):
        deleted_patterns.append(pattern)

    monkeypatch.setattr(tasks.CacheService, "delete_pattern", fake_delete_pattern, raising=False)
    monkeypatch.setattr(tasks, "async_session_maker", session_maker, raising=False)

    user = await create_user(db_session, faker)
    location = await create_location(db_session, faker)
    room = await create_room(db_session, faker, location=location)
    timeslot = await create_timeslot(
        db_session,
        room=room,
        start_datetime=datetime.now(timezone.utc) - timedelta(hours=2),
        end_datetime=datetime.now(timezone.utc) - timedelta(hours=1),
    )
    booking = await create_booking(
        db_session,
        user=user,
        room=room,
        timeslot=timeslot,
        expires_delta=timedelta(minutes=-1),
    )
    await db_session.commit()

    result = await tasks._expire_booking(booking.id)

    status_value = result["status"]
    assert str(status_value).endswith("EXPIRED")
    assert any("timeslots" in pattern for pattern in deleted_patterns)
    await db_session.refresh(timeslot)
    assert timeslot.status == TimeSlotStatus.CANCELED


@pytest.mark.asyncio
async def test_expire_booking_does_not_cancel_fixed_timeslot(db_session, session_maker, faker, monkeypatch):
    monkeypatch.setattr(tasks, "async_session_maker", session_maker, raising=False)
    user = await create_user(db_session, faker)
    location = await create_location(db_session, faker)
    room = await create_room(
        db_session,
        faker,
        location=location,
        time_slot_type=TimeSlotType.FIXED,
    )
    timeslot = await create_timeslot(
        db_session,
        room=room,
        start_datetime=datetime.now(timezone.utc) - timedelta(hours=2),
        end_datetime=datetime.now(timezone.utc) - timedelta(hours=1),
    )
    booking = await create_booking(
        db_session,
        user=user,
        room=room,
        timeslot=timeslot,
        expires_delta=timedelta(minutes=-1),
    )
    await db_session.commit()

    result = await tasks._expire_booking(booking.id)

    status_value = result["status"]
    assert str(status_value).endswith("EXPIRED")
    await db_session.refresh(timeslot)
    assert timeslot.status == TimeSlotStatus.AVAILABLE


@pytest.mark.asyncio
async def test_expire_booking_skipped_when_no_engine(monkeypatch):
    monkeypatch.setattr(tasks.db_base, "async_session_maker", None, raising=False)
    monkeypatch.setattr(tasks.db_base, "init_engine", lambda echo=False: None)

    result = await tasks._expire_booking(123)

    assert result["status"] == "skipped_no_engine"


@pytest.mark.asyncio
async def test_expire_booking_returns_error_on_cache_failure(db_session, session_maker, faker, monkeypatch):
    async def fake_delete_pattern(self, pattern: str):
        raise RuntimeError("cache down")

    monkeypatch.setattr(tasks.CacheService, "delete_pattern", fake_delete_pattern, raising=False)
    monkeypatch.setattr(tasks, "async_session_maker", session_maker, raising=False)

    user = await create_user(db_session, faker)
    location = await create_location(db_session, faker)
    room = await create_room(db_session, faker, location=location)
    timeslot = await create_timeslot(
        db_session,
        room=room,
        start_datetime=datetime.now(timezone.utc) - timedelta(hours=2),
        end_datetime=datetime.now(timezone.utc) - timedelta(hours=1),
    )
    booking = await create_booking(
        db_session,
        user=user,
        room=room,
        timeslot=timeslot,
        expires_delta=timedelta(minutes=-1),
    )
    await db_session.commit()

    result = await tasks._expire_booking(booking.id)

    assert result["status"] == "error"
    assert "cache down" in result["detail"]
