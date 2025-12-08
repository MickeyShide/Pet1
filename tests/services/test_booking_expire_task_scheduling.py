from datetime import datetime, timedelta, timezone

import pytest

from app.models import Booking
from app.models.booking import BookingStatus
from app.schemas.auth import SAccessToken
from app.schemas.booking import SBookingCreate
from app.services.business.bookings import BookingsBusinessService
from tests.fixtures.factories import (
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
    await db_session.commit()

    called = {}

    def fake_apply_async(args=None, eta=None, **kwargs):
        called["args"] = args
        called["eta"] = eta
        return None

    monkeypatch.setattr("app.services.business.bookings.expire_booking.apply_async", fake_apply_async)

    service = BookingsBusinessService(token_data=token)
    result = await service.create_booking(SBookingCreate(timeslot_id=slot.id))

    booking_from_db = await db_session.get(Booking, result.id)
    assert called["args"] == [result.id]
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
    await db_session.commit()

    def fake_apply_async(*args, **kwargs):
        raise RuntimeError("broker unavailable")

    monkeypatch.setattr("app.services.business.bookings.expire_booking.apply_async", fake_apply_async)

    service = BookingsBusinessService(token_data=token)
    result = await service.create_booking(SBookingCreate(timeslot_id=slot.id))

    booking_from_db = await db_session.get(Booking, result.id)
    assert booking_from_db is not None
    assert booking_from_db.status == BookingStatus.PENDING_PAYMENTS
