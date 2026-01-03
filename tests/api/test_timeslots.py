from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select

from app.api import deps
from app.schemas.auth import SAccessToken
from app.utils.err.base.forbidden import ForbiddenException
from app.models import TimeSlot
from tests.fixtures.factories import (
    create_location,
    create_room,
    create_timeslot,
)


def override_token(app, *, admin: bool):
    async def fake_token(jwt_token: deps.HTTPBearerDepends):
        return SAccessToken(sub="1", admin=admin)

    async def fake_admin(jwt_token: deps.HTTPBearerDepends):
        if admin:
            return SAccessToken(sub="1", admin=True)
        raise ForbiddenException("Admin required")

    app.dependency_overrides[deps.get_token_data] = fake_token
    app.dependency_overrides[deps.get_admin_token_data] = fake_admin


def auth_header():
    return {"Authorization": "Bearer stub"}


@pytest.mark.asyncio
async def test__get_timeslots_by_range_returns_empty(async_client, db_session, faker):
    location = await create_location(db_session, faker)
    room = await create_room(db_session, faker, location=location)
    await db_session.commit()

    start = datetime.now(timezone.utc)
    end = start + timedelta(hours=1)
    params = {"room_id": room.id, "date_from": start.isoformat(), "date_to": end.isoformat()}
    response = await async_client.get("/timeslots", params=params)

    assert response.status_code == 200, response.text
    assert response.json() == []


@pytest.mark.asyncio
async def test__get_timeslots_by_range_returns_items(async_client, db_session, faker):
    location = await create_location(db_session, faker)
    room = await create_room(db_session, faker, location=location)
    start = datetime(2025, 1, 1, 10, 30, tzinfo=timezone.utc)
    end = start + timedelta(hours=1, minutes=30)
    slot = await create_timeslot(
        db_session,
        room=room,
        start_datetime=start,
        end_datetime=end,
    )
    await db_session.commit()

    params = {
        "room_id": room.id,
        "date_from": (start - timedelta(minutes=5)).isoformat(),
        "date_to": (end + timedelta(minutes=5)).isoformat(),
    }
    response = await async_client.get("/timeslots", params=params)

    assert response.status_code == 200, response.text
    data = response.json()
    assert len(data) == 1
    item = data[0]
    assert item["id"] == str(slot.id)
    assert item["date_from"] == start.isoformat()
    assert item["date_to"] == end.isoformat()
    assert item["label"] == "10:30 - 12:00"
    assert item["hours"] == pytest.approx(1.5)


@pytest.mark.asyncio
async def test__get_timeslots_by_range_missing_room_id_returns_422(async_client):
    start = datetime.now(timezone.utc)
    end = start + timedelta(hours=1)
    params = {"date_from": start.isoformat(), "date_to": end.isoformat()}
    response = await async_client.get("/timeslots", params=params)

    assert response.status_code == 422, response.text


@pytest.mark.asyncio
async def test__get_timeslots_by_range_missing_date_from_returns_422(async_client):
    end = datetime.now(timezone.utc) + timedelta(hours=1)
    params = {"room_id": 1, "date_to": end.isoformat()}
    response = await async_client.get("/timeslots", params=params)

    assert response.status_code == 422, response.text


@pytest.mark.asyncio
async def test__get_timeslots_by_range_missing_date_to_uses_full_day(async_client, db_session, faker):
    location = await create_location(db_session, faker)
    room = await create_room(db_session, faker, location=location)
    start = datetime(2025, 1, 1, 10, 30, tzinfo=timezone.utc)
    end = start + timedelta(hours=1)
    slot = await create_timeslot(
        db_session,
        room=room,
        start_datetime=start,
        end_datetime=end,
    )
    await db_session.commit()

    params = {"room_id": room.id, "date_from": start.isoformat()}
    response = await async_client.get("/timeslots", params=params)

    assert response.status_code == 200, response.text
    data = response.json()
    assert len(data) == 1
    assert data[0]["id"] == str(slot.id)


@pytest.mark.asyncio
async def test__get_timeslots_by_range_invalid_room_id_returns_422(async_client):
    start = datetime.now(timezone.utc)
    end = start + timedelta(hours=1)
    params = {"room_id": "bad", "date_from": start.isoformat(), "date_to": end.isoformat()}
    response = await async_client.get("/timeslots", params=params)

    assert response.status_code == 422, response.text


@pytest.mark.asyncio
async def test__get_timeslots_by_range_invalid_date_from_returns_422(async_client):
    params = {"room_id": 1, "date_from": "not-a-date", "date_to": "2025-01-01T12:00:00Z"}
    response = await async_client.get("/timeslots", params=params)

    assert response.status_code == 422, response.text


@pytest.mark.asyncio
async def test__update_timeslot_requires_admin(async_client, db_session, faker):
    location = await create_location(db_session, faker)
    room = await create_room(db_session, faker, location=location)
    slot = await create_timeslot(
        db_session,
        room=room,
        start_datetime=datetime.now(timezone.utc),
        end_datetime=datetime.now(timezone.utc) + timedelta(hours=1),
    )
    await db_session.commit()
    override_token(async_client.app_ref, admin=False)

    response = await async_client.patch(
        f"/timeslots/{slot.id}",
        json={"base_price": 500},
        headers=auth_header(),
    )

    async_client.app_ref.dependency_overrides.clear()
    assert response.status_code == 403


@pytest.mark.asyncio
async def test__update_timeslot_with_admin(async_client, db_session, faker):
    location = await create_location(db_session, faker)
    room = await create_room(db_session, faker, location=location)
    slot = await create_timeslot(
        db_session,
        room=room,
        start_datetime=datetime.now(timezone.utc),
        end_datetime=datetime.now(timezone.utc) + timedelta(hours=1),
        base_price=100,
    )
    await db_session.commit()
    override_token(async_client.app_ref, admin=True)

    response = await async_client.patch(
        f"/timeslots/{slot.id}",
        json={"base_price": 200},
        headers=auth_header(),
    )

    async_client.app_ref.dependency_overrides.clear()
    assert response.status_code == 200, response.text
    await db_session.refresh(slot)
    assert slot.base_price == 200


@pytest.mark.asyncio
async def test__delete_timeslot_requires_admin(async_client, db_session, faker):
    location = await create_location(db_session, faker)
    room = await create_room(db_session, faker, location=location)
    slot = await create_timeslot(
        db_session,
        room=room,
        start_datetime=datetime.now(timezone.utc),
        end_datetime=datetime.now(timezone.utc) + timedelta(hours=1),
    )
    await db_session.commit()
    override_token(async_client.app_ref, admin=False)

    slot_id = slot.id
    response = await async_client.delete(f"/timeslots/{slot_id}", headers=auth_header())

    async_client.app_ref.dependency_overrides.clear()
    assert response.status_code == 403


@pytest.mark.asyncio
async def test__delete_timeslot_with_admin(async_client, db_session, faker):
    location = await create_location(db_session, faker)
    room = await create_room(db_session, faker, location=location)
    slot = await create_timeslot(
        db_session,
        room=room,
        start_datetime=datetime.now(timezone.utc),
        end_datetime=datetime.now(timezone.utc) + timedelta(hours=1),
    )
    await db_session.commit()
    override_token(async_client.app_ref, admin=True)

    slot_id = slot.id
    response = await async_client.delete(f"/timeslots/{slot_id}", headers=auth_header())

    async_client.app_ref.dependency_overrides.clear()
    assert response.status_code == 204
    db_session.expire_all()
    result = await db_session.execute(
        select(TimeSlot).where(TimeSlot.id == slot_id)
    )
    remaining = result.scalar_one_or_none()
    assert remaining is None


@pytest.mark.asyncio
async def test__update_timeslot_not_found_returns_404(async_client):
    override_token(async_client.app_ref, admin=True)

    response = await async_client.patch(
        "/timeslots/9999",
        json={"base_price": 200},
        headers=auth_header(),
    )

    async_client.app_ref.dependency_overrides.clear()
    assert response.status_code == 404


@pytest.mark.asyncio
async def test__delete_timeslot_not_found_returns_404(async_client):
    override_token(async_client.app_ref, admin=True)

    response = await async_client.delete(
        "/timeslots/9999",
        headers=auth_header(),
    )

    async_client.app_ref.dependency_overrides.clear()
    assert response.status_code == 404
