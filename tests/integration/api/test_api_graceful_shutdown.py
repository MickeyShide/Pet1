import asyncio
from datetime import datetime, timedelta, timezone

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.api import routers
from app.api.routers import system as system_router
from app.graceful_shutdown import get_graceful_shutdown_state, install_graceful_shutdown
from app.models.payment import Payment
from app.repositories.payment import PaymentRepository
from app.schemas.auth import SAccessToken
from app.services.business.payments import PaymentBusinessService
from tests.factories import (
    create_booking,
    create_location,
    create_room,
    create_timeslot,
    create_user,
)
from tests.integration.api.helpers import clear_overrides, override_token


@pytest_asyncio.fixture
async def draining_client(db_session):
    app = FastAPI(title="test-draining-app")
    install_graceful_shutdown(app, retry_after_seconds=15)
    for router in routers.__all__:
        app.include_router(router)

    transport = ASGITransport(app=app, raise_app_exceptions=True)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        client.app_ref = app
        clear_overrides(app)
        yield client
        clear_overrides(app)


@pytest.mark.asyncio
async def test__ready_returns_503_while_draining(draining_client, monkeypatch):
    async def always_true():
        return True

    monkeypatch.setattr(system_router, "_check_db", always_true)
    monkeypatch.setattr(system_router, "_check_redis", always_true)
    monkeypatch.setattr(system_router, "_check_rabbitmq", always_true)

    get_graceful_shutdown_state(draining_client.app_ref).begin_draining("test")

    response = await draining_client.get("/ready")

    assert response.status_code == 503
    assert response.json()["status"] == "draining"
    assert response.json()["shutdown"]["draining"] is True


@pytest.mark.asyncio
async def test__new_mutation_is_rejected_while_draining(draining_client, db_session, faker):
    user = await create_user(db_session, faker)
    token = SAccessToken(sub=str(user.id), admin=False)
    override_token(draining_client.app_ref, token)
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
    await db_session.flush()

    get_graceful_shutdown_state(draining_client.app_ref).begin_draining("test")

    response = await draining_client.post(
        f"/bookings/{booking.id}/payments",
        headers={"Authorization": "Bearer test"},
    )

    clear_overrides(draining_client.app_ref)
    stored_payment = (
        await db_session.execute(select(Payment).where(Payment.booking_id == booking.id))
    ).scalar_one_or_none()

    assert response.status_code == 503
    assert response.headers["Retry-After"] == "15"
    assert stored_payment is None


@pytest.mark.asyncio
async def test__inflight_payment_confirmation_finishes_before_drain_rejects_new_requests(
    draining_client,
    db_session,
    faker,
    monkeypatch,
):
    user = await create_user(db_session, faker)
    token = SAccessToken(sub=str(user.id), admin=False)
    override_token(draining_client.app_ref, token)
    location = await create_location(db_session, faker)
    room = await create_room(db_session, faker, location=location)
    start = datetime.now(timezone.utc) + timedelta(hours=1)
    slot = await create_timeslot(
        db_session,
        room=room,
        start_datetime=start,
        end_datetime=start + timedelta(hours=1),
    )
    booking = await create_booking(db_session, user=user, room=room, timeslot=slot)
    await db_session.flush()
    payment = await PaymentRepository(db_session).create(booking_id=booking.id, external_id="ext-drain")
    await db_session.flush()

    started = asyncio.Event()
    proceed = asyncio.Event()
    original_confirm_payment = PaymentBusinessService.confirm_payment

    async def delayed_confirm_payment(self, payment_id: int):
        started.set()
        await proceed.wait()
        return await original_confirm_payment(self, payment_id)

    monkeypatch.setattr(PaymentBusinessService, "confirm_payment", delayed_confirm_payment)

    request_task = asyncio.create_task(
        draining_client.post(
            f"/payments/{payment.id}/confirm",
            headers={"Authorization": "Bearer test"},
        )
    )

    await started.wait()
    get_graceful_shutdown_state(draining_client.app_ref).begin_draining("test")
    proceed.set()

    response = await request_task
    rejected_response = await draining_client.post(
        f"/bookings/{booking.id}/payments",
        headers={"Authorization": "Bearer test"},
    )

    clear_overrides(draining_client.app_ref)
    await db_session.refresh(booking)
    await db_session.refresh(payment)

    assert response.status_code == 200, response.text
    assert booking.status.value == "PAID"
    assert payment.status.value == "SUCCESS"
    assert rejected_response.status_code == 503
