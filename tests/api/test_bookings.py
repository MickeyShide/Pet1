from datetime import datetime, timedelta, timezone

import pytest
from fastapi import FastAPI

from app.api import deps
from app.models import Booking
from app.models.booking import BookingStatus
from app.schemas.auth import SAccessToken
from tests.fixtures.factories import (
    create_booking,
    create_location,
    create_room,
    create_timeslot,
    create_user,
)


def override_token_dependency(app: FastAPI, token: SAccessToken):
    async def fake_dep():
        return token

    app.dependency_overrides[deps.get_token_data] = fake_dep
    app.dependency_overrides[deps.get_admin_token_data] = fake_dep


@pytest.mark.asyncio
async def test__create_booking_route__creates_booking(async_client, db_session, faker):
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
    await db_session.commit()

    response = await async_client.post("/bookings/", json={"timeslot_id": slot.id})

    async_client.app_ref.dependency_overrides.clear()
    assert response.status_code == 201, response.text
    booking = await db_session.get(Booking, response.json()["id"])
    assert booking is not None
    assert booking.user_id == user.id


@pytest.mark.asyncio
async def test__get_all_user_bookings__applies_status_filter(async_client, db_session, faker):
    user = await create_user(db_session, faker)
    token = SAccessToken(sub=str(user.id), admin=False)
    override_token_dependency(async_client.app_ref, token)
    location = await create_location(db_session, faker)
    room = await create_room(db_session, faker, location=location)
    slot_paid = await create_timeslot(
        db_session,
        room=room,
        start_datetime=datetime.now(timezone.utc),
        end_datetime=datetime.now(timezone.utc) + timedelta(hours=1),
    )
    slot_canceled = await create_timeslot(
        db_session,
        room=room,
        start_datetime=datetime.now(timezone.utc) + timedelta(days=1),
        end_datetime=datetime.now(timezone.utc) + timedelta(days=1, hours=1),
    )
    await create_booking(
        db_session,
        user=user,
        room=room,
        timeslot=slot_paid,
        status=BookingStatus.PAID,
    )
    await create_booking(
        db_session,
        user=user,
        room=room,
        timeslot=slot_canceled,
        status=BookingStatus.CANCELED,
    )
    await db_session.commit()

    response = await async_client.get("/bookings/?status=PAID")

    async_client.app_ref.dependency_overrides.clear()
    assert response.status_code == 200, response.text
    data = response.json()
    assert len(data) == 1
    assert data[0]["booking"]["status"] == BookingStatus.PAID


@pytest.mark.asyncio
async def test__create_booking_route__requires_auth(async_client):
    response = await async_client.post("/bookings/", json={"timeslot_id": 1})
    assert response.status_code == 401


@pytest.mark.asyncio
async def test__create_booking_route__missing_timeslot_id_returns_422(async_client, db_session, faker):
    user = await create_user(db_session, faker)
    token = SAccessToken(sub=str(user.id), admin=False)
    override_token_dependency(async_client.app_ref, token)

    response = await async_client.post("/bookings/", json={})

    async_client.app_ref.dependency_overrides.clear()
    assert response.status_code == 422


@pytest.mark.asyncio
async def test__create_booking_route__invalid_timeslot_id_returns_422(async_client, db_session, faker):
    user = await create_user(db_session, faker)
    token = SAccessToken(sub=str(user.id), admin=False)
    override_token_dependency(async_client.app_ref, token)

    response = await async_client.post("/bookings/", json={"timeslot_id": "abc"})

    async_client.app_ref.dependency_overrides.clear()
    assert response.status_code == 422


@pytest.mark.asyncio
async def test__get_user_bookings_requires_auth(async_client):
    response = await async_client.get("/bookings/")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test__create_booking_route__fails_when_slot_taken(async_client, db_session, faker):
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
    await create_booking(
        db_session,
        user=user,
        room=room,
        timeslot=slot,
        status=BookingStatus.PAID,
    )
    await db_session.commit()

    response = await async_client.post("/bookings/", json={"timeslot_id": slot.id})

    async_client.app_ref.dependency_overrides.clear()
    assert response.status_code == 409


@pytest.mark.asyncio
async def test__get_user_bookings__returns_empty_list_when_none(async_client, db_session, faker):
    user = await create_user(db_session, faker)
    await db_session.commit()
    token = SAccessToken(sub=str(user.id), admin=False)
    override_token_dependency(async_client.app_ref, token)

    response = await async_client.get("/bookings/", headers={"Authorization": "Bearer test"})

    async_client.app_ref.dependency_overrides.clear()
    assert response.status_code == 200, response.text
    assert response.json() == []


@pytest.mark.asyncio
async def test__get_user_bookings__filters_by_room_id(async_client, db_session, faker):
    user = await create_user(db_session, faker)
    token = SAccessToken(sub=str(user.id), admin=False)
    override_token_dependency(async_client.app_ref, token)
    location = await create_location(db_session, faker)
    room_a = await create_room(db_session, faker, location=location)
    room_b = await create_room(db_session, faker, location=location)
    slot_a = await create_timeslot(
        db_session,
        room=room_a,
        start_datetime=datetime.now(timezone.utc),
        end_datetime=datetime.now(timezone.utc) + timedelta(hours=1),
    )
    slot_b = await create_timeslot(
        db_session,
        room=room_b,
        start_datetime=datetime.now(timezone.utc) + timedelta(days=1),
        end_datetime=datetime.now(timezone.utc) + timedelta(days=1, hours=1),
    )
    await create_booking(db_session, user=user, room=room_a, timeslot=slot_a)
    target_booking = await create_booking(db_session, user=user, room=room_b, timeslot=slot_b)
    await db_session.commit()

    response = await async_client.get(f"/bookings/?room_id={room_b.id}")

    async_client.app_ref.dependency_overrides.clear()
    assert response.status_code == 200, response.text
    data = response.json()
    assert len(data) == 1
    assert data[0]["booking"]["id"] == target_booking.id


@pytest.mark.asyncio
async def test__get_user_bookings__filters_by_timeslot_range(async_client, db_session, faker):
    user = await create_user(db_session, faker)
    token = SAccessToken(sub=str(user.id), admin=False)
    override_token_dependency(async_client.app_ref, token)
    location = await create_location(db_session, faker)
    room = await create_room(db_session, faker, location=location)
    start = datetime.now(timezone.utc)
    slot_in_range = await create_timeslot(
        db_session,
        room=room,
        start_datetime=start,
        end_datetime=start + timedelta(hours=1),
    )
    slot_out_of_range = await create_timeslot(
        db_session,
        room=room,
        start_datetime=start + timedelta(days=2),
        end_datetime=start + timedelta(days=2, hours=1),
    )
    target_booking = await create_booking(db_session, user=user, room=room, timeslot=slot_in_range)
    await create_booking(db_session, user=user, room=room, timeslot=slot_out_of_range)
    await db_session.commit()
    params = {
        "start_datetime": (slot_in_range.start_datetime - timedelta(minutes=5)).isoformat(),
        "end_datetime": (slot_in_range.end_datetime + timedelta(minutes=5)).isoformat(),
    }

    response = await async_client.get("/bookings/", params=params)

    async_client.app_ref.dependency_overrides.clear()
    assert response.status_code == 200, response.text
    data = response.json()
    assert len(data) == 1
    assert data[0]["booking"]["id"] == target_booking.id
