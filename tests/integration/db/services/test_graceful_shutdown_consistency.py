import asyncio
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select

from app.models.booking import Booking, BookingStatus
from app.models.payment import Payment, PaymentStatus
from app.schemas.auth import SAccessToken
from app.schemas.booking import SBookingCreate
from app.services.booking import BookingService
from app.services.business.bookings import BookingsBusinessService
from app.services.business.payments import PaymentBusinessService
from tests.factories import (
    create_booking,
    create_location,
    create_room,
    create_timeslot,
    create_user,
)


@pytest.mark.asyncio
async def test__create_booking__rolls_back_on_cancellation_during_shutdown(db_session, faker, monkeypatch):
    user = await create_user(db_session, faker)
    location = await create_location(db_session, faker)
    room = await create_room(db_session, faker, location=location)
    start = datetime.now(timezone.utc)
    slot = await create_timeslot(
        db_session,
        room=room,
        start_datetime=start,
        end_datetime=start + timedelta(hours=1),
    )
    await db_session.flush()

    async def fake_expire_booking(*args, **kwargs):
        raise asyncio.CancelledError

    monkeypatch.setattr(
        "app.celery_app.manager.CeleryManager.expire_booking",
        fake_expire_booking,
    )

    service = BookingsBusinessService(token_data=SAccessToken(sub=str(user.id), admin=False))

    with pytest.raises(asyncio.CancelledError):
        await service.create_booking(SBookingCreate(timeslot_id=slot.id))

    stored_booking = (
        await db_session.execute(select(Booking).where(Booking.timeslot_id == slot.id))
    ).scalar_one_or_none()
    assert stored_booking is None


@pytest.mark.asyncio
async def test__confirm_payment__rolls_back_on_cancellation_during_shutdown(db_session, faker, monkeypatch):
    user = await create_user(db_session, faker)
    token = SAccessToken(sub=str(user.id), admin=False)
    location = await create_location(db_session, faker)
    room = await create_room(db_session, faker, location=location)
    start = datetime.now(timezone.utc) + timedelta(hours=1)
    slot = await create_timeslot(
        db_session,
        room=room,
        start_datetime=start,
        end_datetime=start + timedelta(hours=1),
    )
    booking = await create_booking(
        db_session,
        user=user,
        room=room,
        timeslot=slot,
        status=BookingStatus.PENDING_PAYMENTS,
        expires_delta=timedelta(hours=1),
    )
    await db_session.flush()

    payment = await PaymentBusinessService(token_data=token).create_payment(booking.id)

    async def fake_set_booking_paid(self, booking_id: int):
        raise asyncio.CancelledError

    monkeypatch.setattr(BookingService, "set_booking_paid", fake_set_booking_paid)

    with pytest.raises(asyncio.CancelledError):
        await PaymentBusinessService(token_data=token).confirm_payment(payment.id)

    await db_session.refresh(booking)
    stored_payment = await db_session.get(Payment, payment.id)

    assert booking.status == BookingStatus.PENDING_PAYMENTS
    assert stored_payment is not None
    assert stored_payment.status == PaymentStatus.CREATED
