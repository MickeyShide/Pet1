from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from app.models import Booking, TimeSlot
from app.models.booking import BookingStatus
from app.models.room import TimeSlotType
from app.models.timeslot import TimeSlotStatus
from app.schemas.auth import SAccessToken
from tests.factories import (
    create_location,
    create_room,
    create_timeslot,
    create_user,
)
from tests.integration.api.helpers import clear_overrides, override_token_dependency

@pytest.mark.asyncio
async def test__create_booking_flexible_route__creates_booking(async_client, db_session, faker):
    user = await create_user(db_session, faker)
    token = SAccessToken(sub=str(user.id), admin=False)
    override_token_dependency(async_client.app_ref, token)
    location = await create_location(db_session, faker)
    room = await create_room(
        db_session,
        faker,
        location=location,
        hour_price=Decimal("200.00"),
        min_booking_duration_minutes=60,
        booking_step_minutes=30,
    )
    start = datetime(2024, 1, 1, 10, 0, tzinfo=timezone.utc)
    end = start + timedelta(minutes=90)
    await db_session.flush()

    response = await async_client.post(
        "/bookings/flexible",
        json={
            "room_id": room.id,
            "start_datetime": start.isoformat(),
            "end_datetime": end.isoformat(),
        },
    )

    clear_overrides(async_client.app_ref)
    assert response.status_code == 201, response.text
    data = response.json()
    assert data["booking"]["user_id"] == user.id
    assert data["booking"]["room"]["id"] == room.id
    assert data["booking"]["status"] == BookingStatus.PENDING_PAYMENTS
    assert Decimal(str(data["booking"]["total_price"])) == Decimal("300.00")
    assert data["timeslot"]["room_id"] == room.id
    assert data["timeslot"]["start_datetime"] == start.isoformat()
    assert data["timeslot"]["end_datetime"] == end.isoformat()
    assert data["timeslot"]["status"] == TimeSlotStatus.AVAILABLE
    assert Decimal(str(data["timeslot"]["base_price"])) == Decimal("300.00")

    booking = await db_session.get(Booking, data["booking"]["id"])
    timeslot = await db_session.get(TimeSlot, data["timeslot"]["id"])
    assert booking is not None
    assert timeslot is not None
    assert booking.timeslot_id == timeslot.id


@pytest.mark.asyncio
async def test__create_booking_flexible_route__requires_auth(async_client):
    response = await async_client.post(
        "/bookings/flexible",
        json={
            "room_id": 1,
            "start_datetime": datetime.now(timezone.utc).isoformat(),
            "end_datetime": (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(),
        },
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test__create_booking_flexible_route__missing_room_id_returns_422(async_client, db_session, faker):
    user = await create_user(db_session, faker)
    token = SAccessToken(sub=str(user.id), admin=False)
    override_token_dependency(async_client.app_ref, token)
    start = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
    end = start + timedelta(hours=1)

    response = await async_client.post(
        "/bookings/flexible",
        json={
            "start_datetime": start.isoformat(),
            "end_datetime": end.isoformat(),
        },
    )

    clear_overrides(async_client.app_ref)
    assert response.status_code == 422


@pytest.mark.asyncio
async def test__create_booking_flexible_route__missing_start_datetime_returns_422(async_client, db_session, faker):
    user = await create_user(db_session, faker)
    token = SAccessToken(sub=str(user.id), admin=False)
    override_token_dependency(async_client.app_ref, token)
    end = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)

    response = await async_client.post(
        "/bookings/flexible",
        json={
            "room_id": 1,
            "end_datetime": end.isoformat(),
        },
    )

    clear_overrides(async_client.app_ref)
    assert response.status_code == 422


@pytest.mark.asyncio
async def test__create_booking_flexible_route__missing_end_datetime_returns_422(async_client, db_session, faker):
    user = await create_user(db_session, faker)
    token = SAccessToken(sub=str(user.id), admin=False)
    override_token_dependency(async_client.app_ref, token)
    start = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)

    response = await async_client.post(
        "/bookings/flexible",
        json={
            "room_id": 1,
            "start_datetime": start.isoformat(),
        },
    )

    clear_overrides(async_client.app_ref)
    assert response.status_code == 422


@pytest.mark.asyncio
async def test__create_booking_flexible_route__extra_field_returns_422(async_client, db_session, faker):
    user = await create_user(db_session, faker)
    token = SAccessToken(sub=str(user.id), admin=False)
    override_token_dependency(async_client.app_ref, token)

    response = await async_client.post(
        "/bookings/flexible",
        json={
            "room_id": 1,
            "start_datetime": datetime.now(timezone.utc).isoformat(),
            "end_datetime": (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(),
            "extra": "field",
        },
    )

    clear_overrides(async_client.app_ref)
    assert response.status_code == 422


@pytest.mark.asyncio
async def test__create_booking_flexible_route__invalid_datetime_returns_422(async_client, db_session, faker):
    user = await create_user(db_session, faker)
    token = SAccessToken(sub=str(user.id), admin=False)
    override_token_dependency(async_client.app_ref, token)

    response = await async_client.post(
        "/bookings/flexible",
        json={
            "room_id": 1,
            "start_datetime": "not-a-date",
            "end_datetime": "also-not-a-date",
        },
    )

    clear_overrides(async_client.app_ref)
    assert response.status_code == 422


@pytest.mark.asyncio
async def test__create_booking_flexible_route__room_not_found_returns_404(async_client, db_session, faker):
    user = await create_user(db_session, faker)
    token = SAccessToken(sub=str(user.id), admin=False)
    override_token_dependency(async_client.app_ref, token)
    await db_session.flush()

    start = datetime(2024, 1, 1, 10, 0, tzinfo=timezone.utc)
    end = start + timedelta(hours=1)
    response = await async_client.post(
        "/bookings/flexible",
        json={
            "room_id": 9999,
            "start_datetime": start.isoformat(),
            "end_datetime": end.isoformat(),
        },
    )

    clear_overrides(async_client.app_ref)
    assert response.status_code == 404


@pytest.mark.asyncio
async def test__create_booking_flexible_route__fixed_room_returns_409(async_client, db_session, faker):
    user = await create_user(db_session, faker)
    token = SAccessToken(sub=str(user.id), admin=False)
    override_token_dependency(async_client.app_ref, token)
    location = await create_location(db_session, faker)
    room = await create_room(
        db_session,
        faker,
        location=location,
        time_slot_type=TimeSlotType.FIXED,
        min_booking_duration_minutes=60,
        booking_step_minutes=30,
    )
    await db_session.flush()

    start = datetime(2024, 1, 1, 10, 0, tzinfo=timezone.utc)
    end = start + timedelta(hours=1)
    response = await async_client.post(
        "/bookings/flexible",
        json={
            "room_id": room.id,
            "start_datetime": start.isoformat(),
            "end_datetime": end.isoformat(),
        },
    )

    clear_overrides(async_client.app_ref)
    assert response.status_code == 409


@pytest.mark.asyncio
async def test__create_booking_flexible_route__invalid_duration_returns_409(async_client, db_session, faker):
    user = await create_user(db_session, faker)
    token = SAccessToken(sub=str(user.id), admin=False)
    override_token_dependency(async_client.app_ref, token)
    location = await create_location(db_session, faker)
    room = await create_room(
        db_session,
        faker,
        location=location,
        min_booking_duration_minutes=120,
        booking_step_minutes=30,
    )
    await db_session.flush()

    start = datetime(2024, 1, 1, 10, 0, tzinfo=timezone.utc)
    end = start + timedelta(minutes=60)
    response = await async_client.post(
        "/bookings/flexible",
        json={
            "room_id": room.id,
            "start_datetime": start.isoformat(),
            "end_datetime": end.isoformat(),
        },
    )

    clear_overrides(async_client.app_ref)
    assert response.status_code == 409


@pytest.mark.asyncio
async def test__create_booking_flexible_route__overlapping_timeslot_returns_409(async_client, db_session, faker):
    user = await create_user(db_session, faker)
    token = SAccessToken(sub=str(user.id), admin=False)
    override_token_dependency(async_client.app_ref, token)
    location = await create_location(db_session, faker)
    room = await create_room(
        db_session,
        faker,
        location=location,
        min_booking_duration_minutes=30,
        booking_step_minutes=30,
    )
    start = datetime(2024, 1, 1, 10, 0, tzinfo=timezone.utc)
    end = start + timedelta(hours=1)
    await create_timeslot(db_session, room=room, start_datetime=start, end_datetime=end)
    await db_session.flush()

    overlap_start = start + timedelta(minutes=30)
    overlap_end = overlap_start + timedelta(hours=1)
    response = await async_client.post(
        "/bookings/flexible",
        json={
            "room_id": room.id,
            "start_datetime": overlap_start.isoformat(),
            "end_datetime": overlap_end.isoformat(),
        },
    )

    clear_overrides(async_client.app_ref)
    assert response.status_code == 409
