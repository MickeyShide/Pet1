from datetime import datetime, timedelta, timezone

import pytest

from app.celery_app import tasks
from app.db import base as db_base
from tests.fixtures import factories

@pytest.mark.asyncio
async def test_expire_booking_skipped_when_not_expired(db_session, session_maker, faker, monkeypatch):
    monkeypatch.setattr(tasks, "async_session_maker", session_maker, raising=False)
    user = await factories.create_user(db_session, faker)
    location = await factories.create_location(db_session, faker)
    room = await factories.create_room(db_session, faker, location=location)
    timeslot = await factories.create_timeslot(
        db_session,
        room=room,
        start_datetime=datetime.now(timezone.utc),
        end_datetime=datetime.now(timezone.utc) + timedelta(hours=1),
    )
    booking = await factories.create_booking(
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

    user = await factories.create_user(db_session, faker)
    location = await factories.create_location(db_session, faker)
    room = await factories.create_room(db_session, faker, location=location)
    timeslot = await factories.create_timeslot(
        db_session,
        room=room,
        start_datetime=datetime.now(timezone.utc) - timedelta(hours=2),
        end_datetime=datetime.now(timezone.utc) - timedelta(hours=1),
    )
    booking = await factories.create_booking(
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

