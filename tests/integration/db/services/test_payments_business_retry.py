from datetime import datetime, timedelta, timezone

import pytest

from app.integrations.payment_gateway import (
    PaymentGatewayDeclinedError,
    PaymentGatewayTimeoutError,
)
from app.models.payment import PaymentStatus
from app.repositories.payment import PaymentRepository
from app.schemas.auth import SAccessToken
from app.services.business import payments as payments_module
from app.services.business.payments import PaymentBusinessService
from app.utils.err.payment import PaymentProviderRejected, PaymentProviderUnavailable
from tests.factories import (
    create_booking,
    create_location,
    create_room,
    create_timeslot,
    create_user,
)


class _RetryCreateGateway:
    def __init__(self):
        self.calls = 0

    async def create_payment(self, booking_id, amount):
        self.calls += 1
        if self.calls < 3:
            raise PaymentGatewayTimeoutError("temporary timeout")
        return "ext-retry-success"

    async def confirm_payment(self, external_id, amount):
        return None


class _DownCreateGateway:
    def __init__(self):
        self.calls = 0

    async def create_payment(self, booking_id, amount):
        self.calls += 1
        raise PaymentGatewayTimeoutError("provider unavailable")

    async def confirm_payment(self, external_id, amount):
        return None


class _DeclineCreateGateway:
    def __init__(self):
        self.calls = 0

    async def create_payment(self, booking_id, amount):
        self.calls += 1
        raise PaymentGatewayDeclinedError("card declined")

    async def confirm_payment(self, external_id, amount):
        return None


class _RetryConfirmGateway:
    def __init__(self):
        self.calls = 0

    async def create_payment(self, booking_id, amount):
        return "ext-confirm-retry"

    async def confirm_payment(self, external_id, amount):
        self.calls += 1
        if self.calls < 3:
            raise PaymentGatewayTimeoutError("temporary timeout")


class _DownConfirmGateway:
    def __init__(self):
        self.calls = 0

    async def create_payment(self, booking_id, amount):
        return "ext-confirm-down"

    async def confirm_payment(self, external_id, amount):
        self.calls += 1
        raise PaymentGatewayTimeoutError("provider unavailable")


class _DeclineConfirmGateway:
    def __init__(self):
        self.calls = 0

    async def create_payment(self, booking_id, amount):
        return "ext-confirm-decline"

    async def confirm_payment(self, external_id, amount):
        self.calls += 1
        raise PaymentGatewayDeclinedError("card declined")


def _patch_retry_settings(monkeypatch, attempts: int = 3):
    monkeypatch.setattr(payments_module.settings, "PAYMENT_RETRY_MAX_ATTEMPTS", attempts, raising=False)
    monkeypatch.setattr(payments_module.settings, "PAYMENT_RETRY_BASE_DELAY_SECONDS", 0.0, raising=False)
    monkeypatch.setattr(payments_module.settings, "PAYMENT_RETRY_MAX_DELAY_SECONDS", 0.0, raising=False)


async def _create_pending_booking(db_session, faker):
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
    )
    await db_session.flush()
    return user, booking


async def _create_pending_booking_with_payment(db_session, faker):
    user, booking = await _create_pending_booking(db_session, faker)
    payment = await PaymentRepository(db_session).create(
        booking_id=booking.id,
        external_id="ext-for-confirm",
    )
    await db_session.flush()
    return user, booking, payment


@pytest.mark.asyncio
async def test__create_payment_business__retries_on_retryable_gateway_error(db_session, faker, monkeypatch):
    user, booking = await _create_pending_booking(db_session, faker)
    _patch_retry_settings(monkeypatch)
    gateway = _RetryCreateGateway()
    monkeypatch.setattr(PaymentBusinessService, "_get_payment_gateway", lambda self: gateway)

    payment = await PaymentBusinessService(token_data=SAccessToken(sub=str(user.id), admin=False)).create_payment(booking.id)

    assert payment.external_id == "ext-retry-success"
    assert gateway.calls == 3


@pytest.mark.asyncio
async def test__create_payment_business__raises_unavailable_when_retry_exhausted(db_session, faker, monkeypatch):
    user, booking = await _create_pending_booking(db_session, faker)
    _patch_retry_settings(monkeypatch, attempts=3)
    gateway = _DownCreateGateway()
    monkeypatch.setattr(PaymentBusinessService, "_get_payment_gateway", lambda self: gateway)

    with pytest.raises(PaymentProviderUnavailable):
        await PaymentBusinessService(token_data=SAccessToken(sub=str(user.id), admin=False)).create_payment(booking.id)

    assert gateway.calls == 3


@pytest.mark.asyncio
async def test__create_payment_business__does_not_retry_non_retryable_gateway_error(db_session, faker, monkeypatch):
    user, booking = await _create_pending_booking(db_session, faker)
    _patch_retry_settings(monkeypatch, attempts=5)
    gateway = _DeclineCreateGateway()
    monkeypatch.setattr(PaymentBusinessService, "_get_payment_gateway", lambda self: gateway)

    with pytest.raises(PaymentProviderRejected):
        await PaymentBusinessService(token_data=SAccessToken(sub=str(user.id), admin=False)).create_payment(booking.id)

    assert gateway.calls == 1


@pytest.mark.asyncio
async def test__confirm_payment_business__retries_on_retryable_gateway_error(db_session, faker, monkeypatch):
    user, _, payment = await _create_pending_booking_with_payment(db_session, faker)
    _patch_retry_settings(monkeypatch)
    gateway = _RetryConfirmGateway()
    monkeypatch.setattr(PaymentBusinessService, "_get_payment_gateway", lambda self: gateway)

    result = await PaymentBusinessService(token_data=SAccessToken(sub=str(user.id), admin=False)).confirm_payment(payment.id)

    assert result.status == PaymentStatus.SUCCESS
    assert gateway.calls == 3


@pytest.mark.asyncio
async def test__confirm_payment_business__raises_unavailable_when_retry_exhausted(db_session, faker, monkeypatch):
    user, _, payment = await _create_pending_booking_with_payment(db_session, faker)
    _patch_retry_settings(monkeypatch, attempts=3)
    gateway = _DownConfirmGateway()
    monkeypatch.setattr(PaymentBusinessService, "_get_payment_gateway", lambda self: gateway)

    with pytest.raises(PaymentProviderUnavailable):
        await PaymentBusinessService(token_data=SAccessToken(sub=str(user.id), admin=False)).confirm_payment(payment.id)

    assert gateway.calls == 3


@pytest.mark.asyncio
async def test__confirm_payment_business__does_not_retry_non_retryable_gateway_error(db_session, faker, monkeypatch):
    user, _, payment = await _create_pending_booking_with_payment(db_session, faker)
    _patch_retry_settings(monkeypatch, attempts=5)
    gateway = _DeclineConfirmGateway()
    monkeypatch.setattr(PaymentBusinessService, "_get_payment_gateway", lambda self: gateway)

    with pytest.raises(PaymentProviderRejected):
        await PaymentBusinessService(token_data=SAccessToken(sub=str(user.id), admin=False)).confirm_payment(payment.id)

    assert gateway.calls == 1
