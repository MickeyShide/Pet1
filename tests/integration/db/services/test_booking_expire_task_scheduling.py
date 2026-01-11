from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select

from app.models import Booking
from app.models.booking import BookingStatus
from app.schemas.auth import SAccessToken
from app.schemas.booking import SBookingCreate, SBookingCreateFlexible
from app.services.business.bookings import BookingsBusinessService
from tests.factories import (
    create_location,
    create_room,
    create_timeslot,
    create_user,
)


@pytest.mark.asyncio
async def test_create_booking_schedules_expire_task(monkeypatch, db_session, faker):
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
    await db_session.flush()

    called = {}

    async def fake_expire_booking(booking):
        called["booking_id"] = booking.id
        called["eta"] = booking.expires_at
        return {}

    monkeypatch.setattr("app.celery_app.manager.CeleryManager.expire_booking", fake_expire_booking)

    service = BookingsBusinessService(token_data=token)
    result = await service.create_booking(SBookingCreate(timeslot_id=slot.id))

    booking_from_db = await db_session.get(Booking, result.id)
    assert called["booking_id"] == result.id
    assert called["eta"] == booking_from_db.expires_at


@pytest.mark.asyncio
async def test_create_booking_ignores_task_errors(monkeypatch, db_session, faker):
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
    await db_session.flush()

    async def fake_expire_booking(*args, **kwargs):
        raise RuntimeError("broker unavailable")

    monkeypatch.setattr("app.celery_app.manager.CeleryManager.expire_booking", fake_expire_booking)

    service = BookingsBusinessService(token_data=token)
    with pytest.raises(RuntimeError):
        await service.create_booking(SBookingCreate(timeslot_id=slot.id))

    assert (await db_session.execute(select(Booking))).scalars().all() == []


@pytest.mark.asyncio
async def test_create_booking_flexible_schedules_expire_task(monkeypatch, db_session, faker):
    user = await create_user(db_session, faker)
    token = SAccessToken(sub=str(user.id), admin=False)
    location = await create_location(db_session, faker)
    room = await create_room(db_session, faker, location=location)
    start = datetime(2024, 1, 1, 10, 0, tzinfo=timezone.utc)
    end = start + timedelta(hours=1)
    await db_session.flush()

    called = {}

    async def fake_expire_booking(booking):
        called["booking_id"] = booking.id
        called["eta"] = booking.expires_at
        return {}

    monkeypatch.setattr("app.celery_app.manager.CeleryManager.expire_booking", fake_expire_booking)

    service = BookingsBusinessService(token_data=token)
    result = await service.create_booking_flexible(
        SBookingCreateFlexible(room_id=room.id, start_datetime=start, end_datetime=end)
    )

    booking_from_db = await db_session.get(Booking, result.booking.id)
    assert called["booking_id"] == result.booking.id
    assert called["eta"] == booking_from_db.expires_at


@pytest.mark.asyncio
async def test_create_booking_flexible_ignores_task_errors(monkeypatch, db_session, faker):
    user = await create_user(db_session, faker)
    token = SAccessToken(sub=str(user.id), admin=False)
    location = await create_location(db_session, faker)
    room = await create_room(db_session, faker, location=location)
    start = datetime(2024, 1, 1, 10, 0, tzinfo=timezone.utc)
    end = start + timedelta(hours=1)
    await db_session.flush()

    async def fake_expire_booking(*args, **kwargs):
        raise RuntimeError("broker unavailable")

    monkeypatch.setattr("app.celery_app.manager.CeleryManager.expire_booking", fake_expire_booking)

    service = BookingsBusinessService(token_data=token)
    with pytest.raises(RuntimeError):
        await service.create_booking_flexible(
            SBookingCreateFlexible(room_id=room.id, start_datetime=start, end_datetime=end)
        )

    assert (await db_session.execute(select(Booking))).scalars().all() == []
