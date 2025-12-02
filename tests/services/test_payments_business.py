from datetime import datetime, timedelta, timezone

import pytest

from app.models.booking import BookingStatus
from app.models.payment import PaymentStatus
from app.schemas.auth import SAccessToken
from app.services.business.payments import PaymentBusinessService
from app.utils.err.booking import BookingNotFound
from app.utils.err.payment import PaymentNotFound
from tests.fixtures.factories import (
    create_booking,
    create_location,
    create_room,
    create_timeslot,
    create_user,
)


@pytest.mark.asyncio
async def test__create_payment_business__owner_can_create(db_session, faker):
    # Given
    user = await create_user(db_session, faker)
    token = SAccessToken(sub=str(user.id), admin=False)
    location = await create_location(db_session, faker)
    room = await create_room(db_session, faker, location=location)
    start = datetime.now(timezone.utc)
    slot = await create_timeslot(
        db_session,
        room=room,
        start_datetime=start,
        end_datetime=start + timedelta(hours=1),
    )
    booking = await create_booking(db_session, user=user, room=room, timeslot=slot)
    await db_session.commit()
    service = PaymentBusinessService(token_data=token)

    # When
    payment = await service.create_payment(booking_id=booking.id)

    # Then
    assert payment.booking_id == booking.id
    assert payment.status == PaymentStatus.CREATED


@pytest.mark.asyncio
async def test__create_payment_business__other_user_forbidden(db_session, faker):
    # Given
    owner = await create_user(db_session, faker)
    other = await create_user(db_session, faker)
    token = SAccessToken(sub=str(other.id), admin=False)
    location = await create_location(db_session, faker)
    room = await create_room(db_session, faker, location=location)
    start = datetime.now(timezone.utc)
    slot = await create_timeslot(
        db_session,
        room=room,
        start_datetime=start,
        end_datetime=start + timedelta(hours=1),
    )
    booking = await create_booking(db_session, user=owner, room=room, timeslot=slot)
    await db_session.commit()
    service = PaymentBusinessService(token_data=token)

    # When / Then
    with pytest.raises(BookingNotFound):
        await service.create_payment(booking_id=booking.id)


@pytest.mark.asyncio
async def test__confirm_payment_business__owner_success_sets_status(db_session, faker):
    # Given
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
    await db_session.commit()
    payment = await PaymentBusinessService(token_data=token).create_payment(booking_id=booking.id)

    service = PaymentBusinessService(token_data=token)

    # When
    result = await service.confirm_payment(payment.id)

    # Then
    assert result.status == PaymentStatus.SUCCESS
    await db_session.refresh(booking)
    assert booking.status == BookingStatus.PAID


@pytest.mark.asyncio
async def test__confirm_payment_business__non_owner_forbidden(db_session, faker):
    # Given
    owner = await create_user(db_session, faker)
    other = await create_user(db_session, faker)
    token = SAccessToken(sub=str(other.id), admin=False)
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
        user=owner,
        room=room,
        timeslot=slot,
        status=BookingStatus.PENDING_PAYMENTS,
        expires_delta=timedelta(hours=1),
    )
    await db_session.commit()
    payment = await PaymentBusinessService(token_data=SAccessToken(sub=str(owner.id), admin=False)).create_payment(
        booking_id=booking.id
    )

    service = PaymentBusinessService(token_data=token)

    # When / Then
    with pytest.raises(PaymentNotFound):
        await service.confirm_payment(payment.id)


@pytest.mark.asyncio
async def test__confirm_payment_business__missing_payment_raises(db_session):
    token = SAccessToken(sub="1", admin=True)
    service = PaymentBusinessService(token_data=token)
    with pytest.raises(PaymentNotFound):
        await service.confirm_payment(payment_id=9999)
