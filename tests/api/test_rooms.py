from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select

from app.api import deps
from app.models import Room, TimeSlot
from app.schemas.auth import SAccessToken
from app.utils.err.base.forbidden import ForbiddenException
from tests.fixtures.factories import (
    create_location,
    create_room,
    create_timeslot,
    create_booking,
    create_user,
)


def override_token(app, *, admin: bool):
    async def fake_dep(jwt_token: deps.HTTPBearerDepends):
        return SAccessToken(sub="1", admin=admin)

    async def fake_admin_dep(jwt_token: deps.HTTPBearerDepends):
        if admin:
            return SAccessToken(sub="1", admin=True)
        raise ForbiddenException("Admin required")

    app.dependency_overrides[deps.get_token_data] = fake_dep
    app.dependency_overrides[deps.get_admin_token_data] = fake_admin_dep


def auth_header():
    return {"Authorization": "Bearer stub"}


@pytest.mark.asyncio
async def test__update_room_requires_admin(async_client, db_session, faker):
    location = await create_location(db_session, faker)
    room = await create_room(db_session, faker, location=location)
    await db_session.commit()
    override_token(async_client.app_ref, admin=False)

    response = await async_client.patch(
        f"/rooms/{room.id}",
        json={"name": "New name"},
        headers=auth_header(),
    )

    async_client.app_ref.dependency_overrides.clear()
    assert response.status_code == 403


@pytest.mark.asyncio
async def test__update_room_with_admin(async_client, db_session, faker):
    location = await create_location(db_session, faker)
    room = await create_room(db_session, faker, location=location)
    await db_session.commit()
    override_token(async_client.app_ref, admin=True)

    response = await async_client.patch(
        f"/rooms/{room.id}",
        json={"name": "Updated room"},
        headers=auth_header(),
    )

    async_client.app_ref.dependency_overrides.clear()
    assert response.status_code == 200, response.text
    await db_session.refresh(room)
    assert room.name == "Updated room"


@pytest.mark.asyncio
async def test__create_room_timeslot_requires_admin(async_client, db_session, faker):
    location = await create_location(db_session, faker)
    room = await create_room(db_session, faker, location=location)
    await db_session.commit()
    override_token(async_client.app_ref, admin=False)

    start = datetime.now(timezone.utc)
    payload = {
        "start_datetime": start.isoformat(),
        "end_datetime": (start + timedelta(hours=1)).isoformat(),
        "base_price": 150,
        "status": "AVAILABLE",
    }

    response = await async_client.post(
        f"/rooms/{room.id}/timeslots",
        json=payload,
        headers=auth_header(),
    )

    async_client.app_ref.dependency_overrides.clear()
    assert response.status_code == 403


@pytest.mark.asyncio
async def test__create_room_timeslot_with_admin(async_client, db_session, faker):
    location = await create_location(db_session, faker)
    room = await create_room(db_session, faker, location=location)
    await db_session.commit()
    override_token(async_client.app_ref, admin=True)

    start = datetime.now(timezone.utc)
    payload = {
        "start_datetime": start.isoformat(),
        "end_datetime": (start + timedelta(hours=2)).isoformat(),
        "base_price": 250,
        "status": "AVAILABLE",
    }

    response = await async_client.post(
        f"/rooms/{room.id}/timeslots",
        json=payload,
        headers=auth_header(),
    )

    async_client.app_ref.dependency_overrides.clear()
    assert response.status_code == 201, response.text
    created_id = response.json()["id"]
    stored = await db_session.get(TimeSlot, created_id)
    assert stored is not None
    assert stored.room_id == room.id


@pytest.mark.asyncio
async def test__get_room_by_id_returns_data(async_client, db_session, faker):
    location = await create_location(db_session, faker)
    room = await create_room(db_session, faker, location=location)
    await db_session.commit()

    response = await async_client.get(f"/rooms/{room.id}")

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == room.id
    assert data["name"] == room.name


@pytest.mark.asyncio
async def test__get_all_rooms_returns_empty(async_client):
    response = await async_client.get("/rooms")

    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test__get_all_rooms_returns_locations(async_client, db_session, faker):
    location = await create_location(db_session, faker)
    room_a = await create_room(db_session, faker, location=location)
    room_b = await create_room(db_session, faker, location=location)
    await db_session.commit()

    response = await async_client.get("/rooms")

    assert response.status_code == 200
    payload = response.json()
    ids = {item["id"] for item in payload}
    assert {room_a.id, room_b.id}.issubset(ids)
    for item in payload:
        assert item["location"]["id"] == location.id


@pytest.mark.asyncio
async def test__get_room_timeslots_returns_booking_flags(async_client, db_session, faker):
    user = await create_user(db_session, faker)
    location = await create_location(db_session, faker)
    room = await create_room(db_session, faker, location=location)
    start = datetime.now(timezone.utc)
    slot_with_booking = await create_timeslot(
        db_session,
        room=room,
        start_datetime=start,
        end_datetime=start + timedelta(hours=1),
    )
    slot_free = await create_timeslot(
        db_session,
        room=room,
        start_datetime=start + timedelta(hours=2),
        end_datetime=start + timedelta(hours=3),
    )
    await create_booking(db_session, user=user, room=room, timeslot=slot_with_booking)
    await db_session.commit()

    params = {
        "date_from": (start - timedelta(minutes=10)).isoformat(),
        "date_to": (slot_free.end_datetime + timedelta(minutes=10)).isoformat(),
    }
    response = await async_client.get(
        f"/rooms/{room.id}/timeslots",
        params=params,
    )

    assert response.status_code == 200, response.text
    data = response.json()
    assert len(data) == 2
    flag_map = {item["id"]: item["has_active_booking"] for item in data}
    assert flag_map[slot_with_booking.id] is True
    assert flag_map[slot_free.id] is False


@pytest.mark.asyncio
async def test__get_room_timeslots_accepts_query_params(async_client, db_session, faker):
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

    params = {
        "date_from": (slot.start_datetime - timedelta(minutes=5)).isoformat(),
        "date_to": (slot.end_datetime + timedelta(minutes=5)).isoformat(),
    }
    response = await async_client.get(f"/rooms/{room.id}/timeslots", params=params)

    assert response.status_code == 200, response.text
    assert len(response.json()) == 1


@pytest.mark.asyncio
async def test__delete_room_requires_admin(async_client, db_session, faker):
    location = await create_location(db_session, faker)
    room = await create_room(db_session, faker, location=location)
    await db_session.commit()
    override_token(async_client.app_ref, admin=False)

    response = await async_client.delete(
        f"/rooms/{room.id}",
        headers=auth_header(),
    )

    async_client.app_ref.dependency_overrides.clear()
    assert response.status_code == 403


@pytest.mark.asyncio
async def test__delete_room_with_admin(async_client, db_session, faker):
    location = await create_location(db_session, faker)
    room = await create_room(db_session, faker, location=location)
    await db_session.commit()
    override_token(async_client.app_ref, admin=True)

    response = await async_client.delete(
        f"/rooms/{room.id}",
        headers=auth_header(),
    )

    async_client.app_ref.dependency_overrides.clear()
    assert response.status_code == 204
    result = await db_session.execute(select(Room.id).where(Room.id == room.id))
    assert result.scalar_one_or_none() is None


@pytest.mark.asyncio
async def test__get_room_by_id_not_found_returns_404(async_client):
    response = await async_client.get("/rooms/99999")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test__update_room_with_admin_not_found(async_client):
    override_token(async_client.app_ref, admin=True)

    response = await async_client.patch(
        "/rooms/9999",
        json={"name": "Missing"},
        headers=auth_header(),
    )

    async_client.app_ref.dependency_overrides.clear()
    assert response.status_code == 404


@pytest.mark.asyncio
async def test__delete_room_with_admin_not_found(async_client):
    override_token(async_client.app_ref, admin=True)

    response = await async_client.delete(
        "/rooms/9999",
        headers=auth_header(),
    )

    async_client.app_ref.dependency_overrides.clear()
    assert response.status_code == 404
