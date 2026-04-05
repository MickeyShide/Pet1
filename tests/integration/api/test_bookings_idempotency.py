from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from fakeredis.aioredis import FakeRedis
from sqlalchemy import func, select

from app.models.booking import Booking
from app.schemas.auth import SAccessToken
from tests.factories import create_location, create_room, create_timeslot, create_user
from tests.integration.api.helpers import clear_overrides, override_token_dependency


@pytest.fixture
def fake_redis(monkeypatch):
    redis = FakeRedis(decode_responses=True)

    async def _fake_get_redis():
        return redis

    monkeypatch.setattr("app.services.business.bookings.get_redis", _fake_get_redis)
    return redis


@pytest.mark.asyncio
async def test__create_booking_route__idempotency_key_returns_same_booking(async_client, db_session, faker, fake_redis):
    user = await create_user(db_session, faker)
    token = SAccessToken(sub=str(user.id), admin=False)
    override_token_dependency(async_client.app_ref, token)
    location = await create_location(db_session, faker)
    room = await create_room(db_session, faker, location=location)
    slot = await create_timeslot(
        db_session,
        room=room,
        start_datetime=datetime.now(timezone.utc),
        end_datetime=datetime.now(timezone.utc) + timedelta(hours=1),
    )
    await db_session.flush()

    idem_key = str(uuid4())
    headers = {"Idempotency-Key": idem_key}
    first = await async_client.post("/bookings", json={"timeslot_id": slot.id}, headers=headers)
    second = await async_client.post("/bookings", json={"timeslot_id": slot.id}, headers=headers)

    clear_overrides(async_client.app_ref)
    assert first.status_code == 201, first.text
    assert second.status_code == 201, second.text
    assert first.json()["id"] == second.json()["id"]

    count_stmt = select(func.count(Booking.id)).where(Booking.timeslot_id == slot.id)
    count = (await db_session.execute(count_stmt)).scalar_one()
    assert count == 1


@pytest.mark.asyncio
async def test__create_booking_route__idempotency_key_with_other_payload_returns_409(async_client, db_session, faker, fake_redis):
    user = await create_user(db_session, faker)
    token = SAccessToken(sub=str(user.id), admin=False)
    override_token_dependency(async_client.app_ref, token)
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

    idem_key = str(uuid4())
    headers = {"Idempotency-Key": idem_key}
    first = await async_client.post("/bookings", json={"timeslot_id": slot_a.id}, headers=headers)
    second = await async_client.post("/bookings", json={"timeslot_id": slot_b.id}, headers=headers)

    clear_overrides(async_client.app_ref)
    assert first.status_code == 201, first.text
    assert second.status_code == 409, second.text
    assert second.json()["detail"] == "Idempotency key is already used with another payload"


@pytest.mark.asyncio
async def test__create_booking_route__invalid_idempotency_key_returns_422(async_client, db_session, faker):
    user = await create_user(db_session, faker)
    token = SAccessToken(sub=str(user.id), admin=False)
    override_token_dependency(async_client.app_ref, token)

    response = await async_client.post(
        "/bookings",
        json={"timeslot_id": 1},
        headers={"Idempotency-Key": "not-a-uuid"},
    )

    clear_overrides(async_client.app_ref)
    assert response.status_code == 422, response.text
