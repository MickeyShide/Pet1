from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest
from sqlalchemy import select

from app.api import deps
from app.models import Room, TimeSlot
from app.models.room import TimeSlotType
from app.schemas.auth import SAccessToken
from app.utils.err.base.forbidden import ForbiddenException
from tests.fixtures.factories import (
    create_location,
    create_room,
    create_timeslot,
    create_booking,
    create_feature,
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
async def test__update_room_requires_auth(async_client, db_session, faker):
    location = await create_location(db_session, faker)
    room = await create_room(db_session, faker, location=location)
    await db_session.commit()

    response = await async_client.patch(
        f"/rooms/{room.id}",
        json={"name": "New name"},
    )

    assert response.status_code == 401


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
async def test__update_room_with_admin_updates_booking_duration_fields(async_client, db_session, faker):
    location = await create_location(db_session, faker)
    room = await create_room(db_session, faker, location=location)
    await db_session.commit()
    override_token(async_client.app_ref, admin=True)

    response = await async_client.patch(
        f"/rooms/{room.id}",
        json={"min_booking_duration_minutes": 90, "booking_step_minutes": 30},
        headers=auth_header(),
    )

    async_client.app_ref.dependency_overrides.clear()
    assert response.status_code == 200, response.text
    await db_session.refresh(room)
    assert room.min_booking_duration_minutes == 90
    assert room.booking_step_minutes == 30


@pytest.mark.asyncio
async def test__update_room_empty_payload_returns_422(async_client, db_session, faker):
    location = await create_location(db_session, faker)
    room = await create_room(db_session, faker, location=location)
    await db_session.commit()
    override_token(async_client.app_ref, admin=True)

    response = await async_client.patch(
        f"/rooms/{room.id}",
        json={},
        headers=auth_header(),
    )

    async_client.app_ref.dependency_overrides.clear()
    assert response.status_code == 422, response.text


@pytest.mark.asyncio
async def test__update_room_invalid_time_slot_type_returns_422(async_client, db_session, faker):
    location = await create_location(db_session, faker)
    room = await create_room(db_session, faker, location=location)
    await db_session.commit()
    override_token(async_client.app_ref, admin=True)

    response = await async_client.patch(
        f"/rooms/{room.id}",
        json={"time_slot_type": "WRONG"},
        headers=auth_header(),
    )

    async_client.app_ref.dependency_overrides.clear()
    assert response.status_code == 422, response.text


@pytest.mark.asyncio
async def test__update_room_with_admin_updates_pricing(async_client, db_session, faker):
    location = await create_location(db_session, faker)
    room = await create_room(db_session, faker, location=location)
    await db_session.commit()
    override_token(async_client.app_ref, admin=True)

    response = await async_client.patch(
        f"/rooms/{room.id}",
        json={"hour_price": "250.00", "time_slot_type": "FIXED"},
        headers=auth_header(),
    )

    async_client.app_ref.dependency_overrides.clear()
    assert response.status_code == 200, response.text
    await db_session.refresh(room)
    assert str(room.hour_price) == "250.00"
    assert room.time_slot_type.value == "FIXED"


@pytest.mark.asyncio
async def test__create_room_timeslot_requires_admin(async_client, db_session, faker):
    location = await create_location(db_session, faker)
    room = await create_room(db_session, faker, location=location)
    await db_session.commit()
    override_token(async_client.app_ref, admin=False)

    start = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
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

    start = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
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
async def test__create_room_timeslot_invalid_payload_returns_422(async_client, db_session, faker):
    location = await create_location(db_session, faker)
    room = await create_room(db_session, faker, location=location)
    await db_session.commit()
    override_token(async_client.app_ref, admin=True)

    payload = {
        "start_datetime": datetime(2024, 1, 1, 10, 0, tzinfo=timezone.utc).isoformat(),
        "base_price": 150,
        "status": "AVAILABLE",
    }

    response = await async_client.post(
        f"/rooms/{room.id}/timeslots",
        json=payload,
        headers=auth_header(),
    )

    async_client.app_ref.dependency_overrides.clear()
    assert response.status_code == 422, response.text


@pytest.mark.asyncio
async def test__create_room_timeslot_invalid_status_returns_422(async_client, db_session, faker):
    location = await create_location(db_session, faker)
    room = await create_room(db_session, faker, location=location)
    await db_session.commit()
    override_token(async_client.app_ref, admin=True)

    start = datetime(2024, 1, 1, 10, 0, tzinfo=timezone.utc)
    payload = {
        "start_datetime": start.isoformat(),
        "end_datetime": (start + timedelta(hours=1)).isoformat(),
        "base_price": 150,
        "status": "BROKEN",
    }

    response = await async_client.post(
        f"/rooms/{room.id}/timeslots",
        json=payload,
        headers=auth_header(),
    )

    async_client.app_ref.dependency_overrides.clear()
    assert response.status_code == 422, response.text


@pytest.mark.asyncio
async def test__create_room_timeslot_missing_room_returns_404(async_client):
    override_token(async_client.app_ref, admin=True)
    start = datetime(2024, 1, 1, 10, 0, tzinfo=timezone.utc)
    payload = {
        "start_datetime": start.isoformat(),
        "end_datetime": (start + timedelta(hours=1)).isoformat(),
        "base_price": 150,
        "status": "AVAILABLE",
    }

    response = await async_client.post(
        "/rooms/9999/timeslots",
        json=payload,
        headers=auth_header(),
    )

    async_client.app_ref.dependency_overrides.clear()
    assert response.status_code == 404


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
    assert data["min_booking_duration_minutes"] == room.min_booking_duration_minutes
    assert data["booking_step_minutes"] == room.booking_step_minutes


@pytest.mark.asyncio
async def test__get_room_by_id_includes_features(async_client, db_session, faker):
    location = await create_location(db_session, faker)
    room = await create_room(db_session, faker, location=location)
    feature = await create_feature(db_session, faker, room=room, name="Projector")
    await db_session.commit()

    response = await async_client.get(f"/rooms/{room.id}")

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["id"] == room.id
    assert payload["features"]
    feature_payload = payload["features"][0]
    assert feature_payload["id"] == feature.id
    assert feature_payload["name"] == "Projector"
    assert feature_payload["room_id"] == room.id


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
        assert item["min_booking_duration_minutes"] is not None
        assert item["booking_step_minutes"] is not None


@pytest.mark.asyncio
async def test__get_room_timeslots_returns_booking_flags(async_client, db_session, faker):
    user = await create_user(db_session, faker)
    location = await create_location(db_session, faker)
    room = await create_room(db_session, faker, location=location)
    start = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
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
async def test__get_room_timeslots_missing_date_from_returns_422(async_client, db_session, faker):
    location = await create_location(db_session, faker)
    room = await create_room(db_session, faker, location=location)
    await db_session.commit()

    response = await async_client.get(f"/rooms/{room.id}/timeslots")

    assert response.status_code == 422, response.text


@pytest.mark.asyncio
async def test__get_room_timeslots_invalid_date_from_returns_422(async_client, db_session, faker):
    location = await create_location(db_session, faker)
    room = await create_room(db_session, faker, location=location)
    await db_session.commit()

    response = await async_client.get(
        f"/rooms/{room.id}/timeslots", params={"date_from": "not-a-date"}
    )

    assert response.status_code == 422, response.text


@pytest.mark.asyncio
async def test__get_room_timeslots_missing_date_to_uses_full_day(async_client, db_session, faker):
    location = await create_location(db_session, faker)
    room = await create_room(db_session, faker, location=location)
    start = datetime(2025, 1, 1, 10, 30, tzinfo=timezone.utc)
    slot = await create_timeslot(
        db_session,
        room=room,
        start_datetime=start,
        end_datetime=start + timedelta(hours=1),
    )
    await db_session.commit()

    response = await async_client.get(
        f"/rooms/{room.id}/timeslots",
        params={"date_from": start.isoformat()},
    )

    assert response.status_code == 200, response.text
    data = response.json()
    assert len(data) == 1
    assert data[0]["id"] == slot.id

@pytest.mark.asyncio
async def test__get_room_timeslots_accepts_query_params(async_client, db_session, faker):
    location = await create_location(db_session, faker)
    room = await create_room(db_session, faker, location=location)
    start = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
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
async def test__get_room_timeslots_missing_room_returns_404(async_client):
    response = await async_client.get(
        "/rooms/9999/timeslots",
        params={"date_from": datetime(2024, 1, 1, 10, 0, tzinfo=timezone.utc).isoformat()},
    )

    assert response.status_code == 404


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


@pytest.mark.asyncio
async def test__get_price_quote_requires_auth(async_client, db_session, faker):
    location = await create_location(db_session, faker)
    room = await create_room(db_session, faker, location=location)
    await db_session.commit()
    start = datetime(2024, 1, 1, 10, 0, tzinfo=timezone.utc)
    payload = {
        "date_from": start.isoformat(),
        "date_to": (start + timedelta(hours=1)).isoformat(),
    }

    response = await async_client.post(
        f"/rooms/{room.id}/price-quote",
        json=payload,
    )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test__get_price_quote_returns_price(async_client, db_session, faker):
    location = await create_location(db_session, faker)
    room = await create_room(
        db_session,
        faker,
        location=location,
        hour_price=Decimal(150),
        time_slot_type=TimeSlotType.FLEXIBLE,
    )
    await db_session.commit()
    override_token(async_client.app_ref, admin=False)
    start = datetime(2024, 1, 1, 10, 0, tzinfo=timezone.utc)
    payload = {
        "date_from": start.isoformat(),
        "date_to": (start + timedelta(hours=2)).isoformat(),
    }

    response = await async_client.post(
        f"/rooms/{room.id}/price-quote",
        json=payload,
        headers=auth_header(),
    )

    async_client.app_ref.dependency_overrides.clear()
    assert response.status_code == 200, response.text
    price_value = response.json()["price"]
    assert Decimal(str(price_value)) == Decimal("300.00")


@pytest.mark.asyncio
async def test__get_price_quote_invalid_dates_returns_422(async_client, db_session, faker):
    location = await create_location(db_session, faker)
    room = await create_room(db_session, faker, location=location)
    await db_session.commit()
    override_token(async_client.app_ref, admin=False)
    start = datetime(2024, 1, 1, 10, 0, tzinfo=timezone.utc)
    payload = {
        "date_from": start.isoformat(),
        "date_to": start.isoformat(),
    }

    response = await async_client.post(
        f"/rooms/{room.id}/price-quote",
        json=payload,
        headers=auth_header(),
    )

    async_client.app_ref.dependency_overrides.clear()
    assert response.status_code == 422, response.text


@pytest.mark.asyncio
async def test__get_price_quote_missing_date_from_returns_422(async_client, db_session, faker):
    location = await create_location(db_session, faker)
    room = await create_room(db_session, faker, location=location)
    await db_session.commit()
    override_token(async_client.app_ref, admin=False)
    end = datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc)
    payload = {
        "date_to": end.isoformat(),
    }

    response = await async_client.post(
        f"/rooms/{room.id}/price-quote",
        json=payload,
        headers=auth_header(),
    )

    async_client.app_ref.dependency_overrides.clear()
    assert response.status_code == 422, response.text


@pytest.mark.asyncio
async def test__get_price_quote_missing_date_to_returns_422(async_client, db_session, faker):
    location = await create_location(db_session, faker)
    room = await create_room(db_session, faker, location=location)
    await db_session.commit()
    override_token(async_client.app_ref, admin=False)
    start = datetime(2024, 1, 1, 10, 0, tzinfo=timezone.utc)
    payload = {
        "date_from": start.isoformat(),
    }

    response = await async_client.post(
        f"/rooms/{room.id}/price-quote",
        json=payload,
        headers=auth_header(),
    )

    async_client.app_ref.dependency_overrides.clear()
    assert response.status_code == 422, response.text


@pytest.mark.asyncio
async def test__get_price_quote_fixed_room_returns_409(async_client, db_session, faker):
    location = await create_location(db_session, faker)
    room = await create_room(
        db_session,
        faker,
        location=location,
        time_slot_type=TimeSlotType.FIXED,
    )
    await db_session.commit()
    override_token(async_client.app_ref, admin=False)
    start = datetime(2024, 1, 1, 10, 0, tzinfo=timezone.utc)
    payload = {
        "date_from": start.isoformat(),
        "date_to": (start + timedelta(hours=1)).isoformat(),
    }

    response = await async_client.post(
        f"/rooms/{room.id}/price-quote",
        json=payload,
        headers=auth_header(),
    )

    async_client.app_ref.dependency_overrides.clear()
    assert response.status_code == 409, response.text


@pytest.mark.asyncio
async def test__get_price_quote_room_not_found_returns_404(async_client, db_session):
    override_token(async_client.app_ref, admin=False)
    start = datetime(2024, 1, 1, 10, 0, tzinfo=timezone.utc)
    payload = {
        "date_from": start.isoformat(),
        "date_to": (start + timedelta(hours=1)).isoformat(),
    }

    response = await async_client.post(
        "/rooms/9999/price-quote",
        json=payload,
        headers=auth_header(),
    )

    async_client.app_ref.dependency_overrides.clear()
    assert response.status_code == 404, response.text


@pytest.mark.asyncio
async def test__get_price_quote_rejects_too_short_duration(async_client, db_session, faker):
    location = await create_location(db_session, faker)
    room = await create_room(
        db_session,
        faker,
        location=location,
        hour_price=Decimal("100.00"),
        min_booking_duration_minutes=120,
        booking_step_minutes=30,
    )
    await db_session.commit()
    override_token(async_client.app_ref, admin=False)
    start = datetime(2024, 1, 1, 10, 0, tzinfo=timezone.utc)
    payload = {
        "date_from": start.isoformat(),
        "date_to": (start + timedelta(minutes=60)).isoformat(),
    }

    response = await async_client.post(
        f"/rooms/{room.id}/price-quote",
        json=payload,
        headers=auth_header(),
    )

    async_client.app_ref.dependency_overrides.clear()
    assert response.status_code == 409, response.text


@pytest.mark.asyncio
async def test__get_price_quote_rejects_unaligned_start(async_client, db_session, faker):
    location = await create_location(db_session, faker)
    room = await create_room(
        db_session,
        faker,
        location=location,
        hour_price=Decimal("100.00"),
        min_booking_duration_minutes=60,
        booking_step_minutes=30,
    )
    await db_session.commit()
    override_token(async_client.app_ref, admin=False)
    start = datetime(2024, 1, 1, 10, 10, tzinfo=timezone.utc)
    payload = {
        "date_from": start.isoformat(),
        "date_to": (start + timedelta(hours=1)).isoformat(),
    }

    response = await async_client.post(
        f"/rooms/{room.id}/price-quote",
        json=payload,
        headers=auth_header(),
    )

    async_client.app_ref.dependency_overrides.clear()
    assert response.status_code == 409, response.text


@pytest.mark.asyncio
async def test__get_price_quote_rejects_unaligned_duration(async_client, db_session, faker):
    location = await create_location(db_session, faker)
    room = await create_room(
        db_session,
        faker,
        location=location,
        hour_price=Decimal("100.00"),
        min_booking_duration_minutes=60,
        booking_step_minutes=30,
    )
    await db_session.commit()
    override_token(async_client.app_ref, admin=False)
    start = datetime(2024, 1, 1, 10, 0, tzinfo=timezone.utc)
    payload = {
        "date_from": start.isoformat(),
        "date_to": (start + timedelta(minutes=45)).isoformat(),
    }

    response = await async_client.post(
        f"/rooms/{room.id}/price-quote",
        json=payload,
        headers=auth_header(),
    )

    async_client.app_ref.dependency_overrides.clear()
    assert response.status_code == 409, response.text


@pytest.mark.asyncio
async def test__get_price_quote_rejects_seconds(async_client, db_session, faker):
    location = await create_location(db_session, faker)
    room = await create_room(
        db_session,
        faker,
        location=location,
        hour_price=Decimal("100.00"),
    )
    await db_session.commit()
    override_token(async_client.app_ref, admin=False)
    start = datetime(2024, 1, 1, 10, 0, 30, tzinfo=timezone.utc)
    payload = {
        "date_from": start.isoformat(),
        "date_to": (start + timedelta(hours=1)).isoformat(),
    }

    response = await async_client.post(
        f"/rooms/{room.id}/price-quote",
        json=payload,
        headers=auth_header(),
    )

    async_client.app_ref.dependency_overrides.clear()
    assert response.status_code == 409, response.text


@pytest.mark.asyncio
async def test__get_price_quote_rejects_end_seconds(async_client, db_session, faker):
    location = await create_location(db_session, faker)
    room = await create_room(
        db_session,
        faker,
        location=location,
        hour_price=Decimal("100.00"),
    )
    await db_session.commit()
    override_token(async_client.app_ref, admin=False)
    start = datetime(2024, 1, 1, 10, 0, tzinfo=timezone.utc)
    end = datetime(2024, 1, 1, 11, 0, 15, tzinfo=timezone.utc)
    payload = {
        "date_from": start.isoformat(),
        "date_to": end.isoformat(),
    }

    response = await async_client.post(
        f"/rooms/{room.id}/price-quote",
        json=payload,
        headers=auth_header(),
    )

    async_client.app_ref.dependency_overrides.clear()
    assert response.status_code == 409, response.text


@pytest.mark.asyncio
async def test__get_price_quote_allows_step_over_hour(async_client, db_session, faker):
    location = await create_location(db_session, faker)
    room = await create_room(
        db_session,
        faker,
        location=location,
        hour_price=Decimal("100.00"),
        min_booking_duration_minutes=90,
        booking_step_minutes=90,
    )
    await db_session.commit()
    override_token(async_client.app_ref, admin=False)
    start = datetime(2024, 1, 1, 1, 30, tzinfo=timezone.utc)
    payload = {
        "date_from": start.isoformat(),
        "date_to": (start + timedelta(minutes=90)).isoformat(),
    }

    response = await async_client.post(
        f"/rooms/{room.id}/price-quote",
        json=payload,
        headers=auth_header(),
    )

    async_client.app_ref.dependency_overrides.clear()
    assert response.status_code == 200, response.text
    price_value = response.json()["price"]
    assert Decimal(str(price_value)) == Decimal("150.00")
