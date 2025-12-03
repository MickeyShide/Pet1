from datetime import datetime, timedelta, timezone

import pytest
import pytest_asyncio
from fastapi import FastAPI
from fakeredis.aioredis import FakeRedis
from httpx import ASGITransport, AsyncClient

from app.api import routers
from app.utils.cache import cache_service as cache_module
from app.services.timeslot import TimeSlotService
from tests.fixtures.factories import create_location, create_room, create_timeslot


@pytest.fixture(scope="session")
def fastapi_app_cache():
    app = FastAPI(title="test-app-cache")
    for router in routers.__all__:
        app.include_router(router)
    return app


@pytest_asyncio.fixture
async def async_client(fastapi_app_cache):
    transport = ASGITransport(app=fastapi_app_cache, raise_app_exceptions=True)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        client.app_ref = fastapi_app_cache
        yield client


@pytest.mark.asyncio
async def test_timeslot_list_is_cached(async_client, db_session, faker, monkeypatch):
    fake_redis = FakeRedis(decode_responses=True)

    async def _fake_get_redis():
        return fake_redis

    monkeypatch.setattr(cache_module, "get_redis", _fake_get_redis)

    call_counter = {"count": 0}
    original_get_all = TimeSlotService.get_all_by_room_id_and_date_range

    async def _wrapped(self, room_id, date_from, date_to):
        call_counter["count"] += 1
        return await original_get_all(self, room_id=room_id, date_from=date_from, date_to=date_to)

    monkeypatch.setattr(TimeSlotService, "get_all_by_room_id_and_date_range", _wrapped)

    location = await create_location(db_session, faker)
    room = await create_room(db_session, faker, location=location)
    start = datetime.now(timezone.utc)
    end = start + timedelta(hours=1)
    await create_timeslot(
        db_session,
        room=room,
        start_datetime=start,
        end_datetime=end,
    )
    await db_session.commit()

    params = {"date_from": start.isoformat(), "date_to": end.isoformat()}

    response_first = await async_client.get(f"/rooms/{room.id}/timeslots", params=params)
    response_second = await async_client.get(f"/rooms/{room.id}/timeslots", params=params)

    assert response_first.status_code == 200
    assert response_second.status_code == 200
    assert call_counter["count"] == 1
    assert response_second.json() == response_first.json()
