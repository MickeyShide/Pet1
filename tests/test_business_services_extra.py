import types
from datetime import datetime, timezone
from decimal import Decimal

import pytest
from starlette.requests import Request
from starlette.responses import Response

from app.models import Booking
from app.models.booking import BookingStatus
from app.models.location import Location
from app.models.user import User, UserRole
from app.schemas.auth import SAccessToken, SLogin
from app.schemas.location import SLocationOut
from app.services.booking import BookingService
from app.services.business.auth import AuthBusinessService
from app.services.business.base import BaseBusinessService
from app.services.business.locations import LocationBusinessService
from app.services.base import BaseService
from app.services.location import LocationService
from app.utils.err.auth import TooManyAttempts


class _DummyLocationService(BaseService[Location]):
    _repository = LocationService._repository  # type: ignore[assignment]


class _DummyBusiness(BaseBusinessService):
    location_service: _DummyLocationService


@pytest.mark.asyncio
async def test_base_business_service_requires_session():
    business = _DummyBusiness()

    with pytest.raises(RuntimeError):
        _ = business.location_service


@pytest.mark.asyncio
async def test_base_business_service_missing_attr_raises():
    business = _DummyBusiness()
    with pytest.raises(AttributeError):
        _ = business.non_existing  # type: ignore[attr-defined]


@pytest.mark.asyncio
async def test_booking_service_cancel_handles_not_canceled(monkeypatch):
    service = BookingService(session=types.SimpleNamespace())

    monkeypatch.setattr(service, "_repository", types.SimpleNamespace(), raising=False)

    async def fake_check_booking_status(**kwargs):
        return BookingStatus.PENDING_PAYMENTS

    async def fake_cancel_booking(**kwargs):
        booking = Booking(
            user_id=1,
            room_id=1,
            timeslot_id=1,
            status=BookingStatus.PENDING_PAYMENTS,
            total_price=Decimal("0"),
            paid_at=None,
            canceled_at=None,
            expires_at=datetime.now(timezone.utc),
        )
        return booking

    service._repository.check_booking_status = fake_check_booking_status  # type: ignore[attr-defined]
    service._repository.cancel_booking = fake_cancel_booking  # type: ignore[attr-defined]

    result = await service.cancel_booking(booking_id=1, user_id=1, is_admin=False)
    assert result is False


@pytest.mark.asyncio
async def test_location_business_service_returns_cached(monkeypatch):
    cached = [SLocationOut(id=1, name="cached", address="addr", description="desc")]

    async def fake_try_get(self, key):
        return cached

    monkeypatch.setattr("app.services.business.locations.CacheService.try_get", fake_try_get, raising=False)

    service = LocationBusinessService()
    result = await service.get_all()

    assert result == cached


@pytest.mark.asyncio
async def test_auth_business_service_blocks_after_many_attempts(monkeypatch):
    class FakeCache:
        def __init__(self, *_, **__):
            self.set_calls = []

        async def try_get(self, key):
            return 5

        async def try_set(self, key, value, ttl=None):
            self.set_calls.append((key, value, ttl))

    monkeypatch.setattr("app.services.business.auth.CacheService", FakeCache)

    # Avoid hitting real user service; it's not used when the antifraud limit is reached.
    service = AuthBusinessService()
    service.user_service = types.SimpleNamespace()

    scope = {"type": "http", "headers": [(b"x-real-ip", b"127.0.0.1")]}
    request = Request(scope)
    response = Response()
    with pytest.raises(TooManyAttempts):
        await service.login(request, response, SLogin(email="x@example.com", password="pwd"))
