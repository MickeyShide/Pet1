from datetime import datetime, timedelta, timezone

import pytest
from fakeredis.aioredis import FakeRedis

from app.schemas.auth import SAccessToken
from app.schemas.booking import SBookingCreate
from app.utils.cache import CacheService, keys as cache_keys
from app.utils.err.base.not_found import NotFoundException
from app.services.business.bookings import BookingsBusinessService
from tests.fixtures.factories import (
    create_booking,
    create_location,
    create_room,
    create_timeslot,
    create_user,
)


@pytest.fixture
def fake_redis(monkeypatch):
    redis = FakeRedis(decode_responses=True)

    async def _fake_get_redis():
        return redis

    monkeypatch.setattr("app.utils.cache.cache_service.get_redis", _fake_get_redis)
    monkeypatch.setattr("app.utils.redis.get_redis", _fake_get_redis)
    return redis


@pytest.mark.asyncio
async def test_create_booking_invalidates_timeslot_cache(fake_redis, db_session, faker):
    user = await create_user(db_session, faker)
    token = SAccessToken(sub=str(user.id), admin=False)
    location = await create_location(db_session, faker)
    room = await create_room(db_session, faker, location=location)
    start = datetime.now(timezone.utc)
    end = start + timedelta(hours=1)
    slot = await create_timeslot(
        db_session,
        room=room,
        start_datetime=start,
        end_datetime=end,
    )
    await db_session.commit()

    cache = CacheService()
    warm_key = cache_keys.timeslots_by_room_and_range(room.id, start, end)
    await cache.set(warm_key, {"cached": True})
    assert await cache.get(warm_key) is not None

    service = BookingsBusinessService(token_data=token)
    await service.create_booking(SBookingCreate(timeslot_id=slot.id))

    assert await cache.get(warm_key) is None


@pytest.mark.asyncio
async def test_cancel_booking_invalidates_timeslot_cache_for_owner(fake_redis, db_session, faker):
    user = await create_user(db_session, faker)
    token = SAccessToken(sub=str(user.id), admin=False)
    location = await create_location(db_session, faker)
    room = await create_room(db_session, faker, location=location)
    start = datetime.now(timezone.utc)
    end = start + timedelta(hours=1)
    slot = await create_timeslot(
        db_session,
        room=room,
        start_datetime=start,
        end_datetime=end,
    )
    booking = await create_booking(db_session, user=user, room=room, timeslot=slot)
    await db_session.commit()

    cache = CacheService()
    warm_key = cache_keys.timeslots_by_room_and_range(room.id, start, end)
    await cache.set(warm_key, {"cached": True})

    service = BookingsBusinessService(token_data=token)
    await service.cancel_booking(booking_id=booking.id)

    assert await cache.get(warm_key) is None


@pytest.mark.asyncio
async def test_cancel_booking_does_not_invalidate_cache_for_foreign_user(fake_redis, db_session, faker):
    owner = await create_user(db_session, faker)
    other = await create_user(db_session, faker)
    token_other = SAccessToken(sub=str(other.id), admin=False)
    location = await create_location(db_session, faker)
    room = await create_room(db_session, faker, location=location)
    start = datetime.now(timezone.utc)
    end = start + timedelta(hours=1)
    slot = await create_timeslot(
        db_session,
        room=room,
        start_datetime=start,
        end_datetime=end,
    )
    booking = await create_booking(db_session, user=owner, room=room, timeslot=slot)
    await db_session.commit()

    cache = CacheService()
    warm_key = cache_keys.timeslots_by_room_and_range(room.id, start, end)
    await cache.set(warm_key, {"cached": True})

    service = BookingsBusinessService(token_data=token_other)
    with pytest.raises(NotFoundException):
        await service.cancel_booking(booking_id=booking.id)

    # Cache for the room should remain intact for unauthorized caller
    assert await cache.get(warm_key) is not None
