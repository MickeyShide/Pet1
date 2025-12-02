from datetime import datetime, timedelta, timezone

import pytest

from app.models.booking import BookingStatus
from app.models.payment import PaymentStatus
from app.services.payment import PaymentService
from app.services.booking import BookingService
from tests.fixtures.factories import (
    create_booking,
    create_location,
    create_room,
    create_timeslot,
    create_user,
)


@pytest.mark.asyncio
async def test__payment_service__create_and_fetch(db_session, faker):
    # Given
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
    booking = await create_booking(db_session, user=user, room=room, timeslot=slot, expires_delta=timedelta(hours=2))
    await db_session.commit()
    service = PaymentService(db_session)

    # When
    payment = await service.create(booking_id=booking.id, external_id="ext-ps-1", status=PaymentStatus.CREATED)

    # Then
    assert payment.booking_id == booking.id
    assert payment.status == PaymentStatus.CREATED
    fetched = await service.get_one_by_id(payment.id)
    assert fetched.id == payment.id


@pytest.mark.asyncio
async def test__payment_service__confirm_sets_booking_paid(db_session, faker):
    # Given
    user = await create_user(db_session, faker)
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
        expires_delta=timedelta(hours=2),
    )
    await db_session.commit()
    payment_service = PaymentService(db_session)
    booking_service = BookingService(db_session)
    payment = await payment_service.create(booking_id=booking.id, external_id="ext-ps-2", status=PaymentStatus.CREATED)

    # When
    updated_payment = await payment_service.update_by_id(payment.id, status=PaymentStatus.SUCCESS)
    updated_booking = await booking_service.set_booking_paid(booking.id)

    # Then
    assert updated_payment.status == PaymentStatus.SUCCESS
    assert updated_booking.status == BookingStatus.PAID
    assert updated_booking.paid_at is not None
