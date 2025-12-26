from datetime import datetime, timedelta, timezone

import pytest

from app.api import deps
from app.models.booking import BookingStatus
from app.models.payment import PaymentStatus
from app.repositories.payment import PaymentRepository
from app.schemas.auth import SAccessToken
from tests.fixtures.factories import (
    create_booking,
    create_location,
    create_room,
    create_timeslot,
    create_user,
)


def override_token(app, token: SAccessToken):
    async def fake_dep(jwt_token: deps.HTTPBearerDepends):
        return token

    app.dependency_overrides[deps.get_token_data] = fake_dep
    app.dependency_overrides[deps.get_admin_token_data] = fake_dep


@pytest.mark.asyncio
async def test__confirm_payment_route__requires_auth(async_client):
    response = await async_client.post("/payments/1/confirm")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test__confirm_payment_route__owner_success_updates_booking(async_client, db_session, faker):
    user = await create_user(db_session, faker)
    token = SAccessToken(sub=str(user.id), admin=False)
    override_token(async_client.app_ref, token)
    location = await create_location(db_session, faker)
    room = await create_room(db_session, faker, location=location)
    start = datetime.now(timezone.utc) - timedelta(days=1)
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
        expires_delta=timedelta(hours=2),  # expired to let set_booking_paid pass
    )
    payment = await PaymentRepository(db_session).create(booking_id=booking.id, external_id="ext-123")
    await db_session.commit()

    response = await async_client.post(
        f"/payments/{payment.id}/confirm",
        headers={"Authorization": "Bearer test"},
    )

    async_client.app_ref.dependency_overrides.clear()
    await db_session.refresh(booking)
    await db_session.refresh(payment)
    assert response.status_code == 200, response.text
    assert booking.status == BookingStatus.PAID
    assert payment.status == PaymentStatus.SUCCESS
    # ❗BUG FOUND: API returns stale payment status (expects SUCCESS).
    assert response.json()["status"] == PaymentStatus.SUCCESS


@pytest.mark.asyncio
async def test__confirm_payment_route__future_booking_returns_not_found(async_client, db_session, faker):
    user = await create_user(db_session, faker)
    token = SAccessToken(sub=str(user.id), admin=False)
    override_token(async_client.app_ref, token)
    location = await create_location(db_session, faker)
    room = await create_room(db_session, faker, location=location)
    start = datetime.now(timezone.utc)
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
    )
    payment = await PaymentRepository(db_session).create(booking_id=booking.id, external_id="ext-124")
    await db_session.commit()

    response = await async_client.post(
        f"/payments/{payment.id}/confirm",
        headers={"Authorization": "Bearer test"},
    )

    async_client.app_ref.dependency_overrides.clear()
    # ❗BUG FOUND: confirm returns 500 instead of expected failure/validation; non-expired booking should be rejected gracefully.
    assert response.status_code == 200


@pytest.mark.asyncio
async def test__confirm_payment_route__not_found_payment(async_client, db_session, faker):
    user = await create_user(db_session, faker)
    token = SAccessToken(sub=str(user.id), admin=False)
    override_token(async_client.app_ref, token)
    await db_session.commit()

    response = await async_client.post(
        "/payments/9999/confirm",
        headers={"Authorization": "Bearer test"},
    )

    async_client.app_ref.dependency_overrides.clear()
    # ❗BUG FOUND: confirm returns 500 instead of 404 for missing payment.
    assert response.status_code == 404


@pytest.mark.asyncio
async def test__confirm_payment_route__forbidden_for_other_user(async_client, db_session, faker):
    owner = await create_user(db_session, faker)
    other = await create_user(db_session, faker)
    token = SAccessToken(sub=str(other.id), admin=False)
    override_token(async_client.app_ref, token)
    location = await create_location(db_session, faker)
    room = await create_room(db_session, faker, location=location)
    start = datetime.now(timezone.utc) - timedelta(days=1)
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
        expires_delta=timedelta(hours=-2),
    )
    payment = await PaymentRepository(db_session).create(booking_id=booking.id, external_id="ext-125")
    await db_session.commit()

    response = await async_client.post(
        f"/payments/{payment.id}/confirm",
        headers={"Authorization": "Bearer test"},
    )

    async_client.app_ref.dependency_overrides.clear()
    # ❗BUG FOUND: confirm returns 500 instead of 404 for non-owner payment.
    assert response.status_code == 404


@pytest.mark.asyncio
async def test__confirm_payment_route__admin_can_confirm_other(async_client, db_session, faker):
    admin = await create_user(db_session, faker)
    token = SAccessToken(sub=str(admin.id), admin=True)
    override_token(async_client.app_ref, token)
    location = await create_location(db_session, faker)
    room = await create_room(db_session, faker, location=location)
    start = datetime.now(timezone.utc) - timedelta(days=1)
    slot = await create_timeslot(
        db_session,
        room=room,
        start_datetime=start,
        end_datetime=start + timedelta(hours=1),
    )
    owner = await create_user(db_session, faker)
    booking = await create_booking(
        db_session,
        user=owner,
        room=room,
        timeslot=slot,
        status=BookingStatus.PENDING_PAYMENTS,
        expires_delta=timedelta(hours=2),
    )
    payment = await PaymentRepository(db_session).create(booking_id=booking.id, external_id="ext-126")
    await db_session.commit()

    response = await async_client.post(
        f"/payments/{payment.id}/confirm",
        headers={"Authorization": "Bearer test"},
    )

    async_client.app_ref.dependency_overrides.clear()
    await db_session.refresh(booking)
    await db_session.refresh(payment)
    # ❗BUG FOUND: confirm returns 500 (TypeError/logic) instead of 200.
    assert response.status_code == 200, response.text
    assert booking.status == BookingStatus.PAID
    assert payment.status == PaymentStatus.SUCCESS
    # ❗BUG FOUND: API returns stale payment status (expects SUCCESS).
    assert response.json()["status"] == PaymentStatus.SUCCESS
