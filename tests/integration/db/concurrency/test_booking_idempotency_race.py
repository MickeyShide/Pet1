import asyncio
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from fakeredis.aioredis import FakeRedis
from sqlalchemy import func, select

from app.models.booking import Booking
from app.schemas.auth import SAccessToken
from app.schemas.booking import SBookingCreate
from app.services.business import bookings as bookings_module
from app.services.business.bookings import BookingsBusinessService
from tests.factories import create_location, create_room, create_timeslot, create_user


@pytest.mark.asyncio
@pytest.mark.concurrent_db
async def test__create_booking_concurrent_same_idempotency_key_returns_same_booking(db_session, faker, monkeypatch):
    redis = FakeRedis(decode_responses=True)

    async def _fake_get_redis():
        return redis

    monkeypatch.setattr("app.services.business.bookings.get_redis", _fake_get_redis)
    monkeypatch.setattr(bookings_module.settings, "BOOKING_IDEMPOTENCY_WAIT_SECONDS", 1.0, raising=False)
    monkeypatch.setattr(bookings_module.settings, "BOOKING_IDEMPOTENCY_POLL_SECONDS", 0.01, raising=False)

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

    token = SAccessToken(sub=str(user.id), admin=False)
    idempotency_key = uuid4()
    start_event = asyncio.Event()

    async def _attempt():
        await start_event.wait()
        service = BookingsBusinessService(token_data=token)
        return await service.create_booking(
            SBookingCreate(timeslot_id=slot.id),
            idempotency_key=idempotency_key,
        )

    task_a = asyncio.create_task(_attempt())
    task_b = asyncio.create_task(_attempt())
    start_event.set()

    results = await asyncio.gather(task_a, task_b, return_exceptions=True)
    successes = [item for item in results if not isinstance(item, Exception)]
    failures = [item for item in results if isinstance(item, Exception)]

    assert not failures
    assert len(successes) == 2
    assert successes[0].id == successes[1].id

    count_stmt = select(func.count(Booking.id)).where(Booking.timeslot_id == slot.id)
    count = (await db_session.execute(count_stmt)).scalar_one()
    assert count == 1
