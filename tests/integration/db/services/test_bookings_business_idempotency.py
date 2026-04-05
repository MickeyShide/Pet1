from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from fakeredis.aioredis import FakeRedis
from sqlalchemy import func, select

from app.models.booking import Booking
from app.schemas.auth import SAccessToken
from app.schemas.booking import SBookingCreate
from app.services.business.bookings import BookingsBusinessService
from app.utils.err.booking import BookingIdempotencyKeyConflict
from tests.factories import create_location, create_room, create_timeslot, create_user


@pytest.fixture
def fake_redis(monkeypatch):
    redis = FakeRedis(decode_responses=True)

    async def _fake_get_redis():
        return redis

    monkeypatch.setattr("app.services.business.bookings.get_redis", _fake_get_redis)
    return redis


@pytest.mark.asyncio
async def test__create_booking__same_idempotency_key_returns_same_booking(fake_redis, db_session, faker):
    user = await create_user(db_session, faker)
    location = await create_location(db_session, faker)
    room = await create_room(db_session, faker, location=location)
    slot = await create_timeslot(
        db_session,
        room=room,
        start_datetime=datetime.now(timezone.utc),
        end_datetime=datetime.now(timezone.utc) + timedelta(hours=1),
    )
    await db_session.flush()

    service = BookingsBusinessService(token_data=SAccessToken(sub=str(user.id), admin=False))
    idem_key = uuid4()

    first = await service.create_booking(SBookingCreate(timeslot_id=slot.id), idempotency_key=idem_key)
    second = await service.create_booking(SBookingCreate(timeslot_id=slot.id), idempotency_key=idem_key)

    assert first.id == second.id
    assert first.timeslot_id == second.timeslot_id == slot.id

    count_stmt = select(func.count(Booking.id)).where(Booking.timeslot_id == slot.id)
    count = (await db_session.execute(count_stmt)).scalar_one()
    assert count == 1


@pytest.mark.asyncio
async def test__create_booking__same_key_with_different_payload_raises_conflict(fake_redis, db_session, faker):
    user = await create_user(db_session, faker)
    location = await create_location(db_session, faker)
    room = await create_room(db_session, faker, location=location)
    slot_a = await create_timeslot(
        db_session,
        room=room,
        start_datetime=datetime.now(timezone.utc),
        end_datetime=datetime.now(timezone.utc) + timedelta(hours=1),
    )
    slot_b = await create_timeslot(
        db_session,
        room=room,
        start_datetime=datetime.now(timezone.utc) + timedelta(hours=2),
        end_datetime=datetime.now(timezone.utc) + timedelta(hours=3),
    )
    await db_session.flush()

    service = BookingsBusinessService(token_data=SAccessToken(sub=str(user.id), admin=False))
    idem_key = uuid4()

    await service.create_booking(SBookingCreate(timeslot_id=slot_a.id), idempotency_key=idem_key)

    with pytest.raises(BookingIdempotencyKeyConflict):
        await service.create_booking(SBookingCreate(timeslot_id=slot_b.id), idempotency_key=idem_key)
