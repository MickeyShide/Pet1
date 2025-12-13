import types
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest
from faker import Faker
from jose import jwt, JWTError
from sqlalchemy.exc import IntegrityError, NoResultFound
from starlette.requests import Request
from starlette.responses import Response

from app.api import deps
from app.config import settings
from app.models import Booking, Payment
from app.models.booking import BookingStatus
from app.schemas.auth import SAccessToken, SLogin, SRefreshToken, SRegister
from app.services.booking import BookingService
from app.services.business.auth import AuthBusinessService
from app.services.business.payments import PaymentBusinessService
from app.services.user import UserService
from app.utils.cache import keys
from app.utils.err.auth import TooManyAttempts, EmailAlreadyTaken
from app.utils.err.base.conflict import ConflictException
from app.utils.err.base.not_found import NotFoundException
from app.utils.err.base.unauthorized import UnauthorizedException
from app.utils.err.booking import BookingNotFound
from app.utils.err.payment import PaymentNotFound
from app.utils.security import create_refresh_token


faker = Faker()


# ---------------- API deps ----------------


@pytest.mark.asyncio
async def test_get_token_data_invalid_signature():
    bad_token = jwt.encode({"sub": "1", "admin": False}, "wrong", algorithm=settings.ALGORITHM)
    credentials = types.SimpleNamespace(credentials=bad_token)

    with pytest.raises(UnauthorizedException):
        await deps.get_token_data(credentials)


@pytest.mark.asyncio
async def test_get_token_data_missing_fields():
    # Missing admin field -> payload invalid
    token = jwt.encode({"sub": "1"}, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    credentials = types.SimpleNamespace(credentials=token)

    with pytest.raises(UnauthorizedException):
        await deps.get_token_data(credentials)


# ---------------- Auth business ----------------

@pytest.mark.asyncio
async def test_auth_login_blocks_on_too_many(monkeypatch):
    class FakeCache:
        def __init__(self):
            self.set_called = False

        async def try_get(self, key):
            return 5

        async def try_set(self, key, value, ttl=None):
            self.set_called = True

    cache = FakeCache()
    monkeypatch.setattr("app.services.business.auth.CacheService", lambda *a, **k: cache)

    service = AuthBusinessService()
    service.user_service = types.SimpleNamespace(login=lambda data: (_ for _ in ()).throw(AssertionError("no call")))

    request = Request({"type": "http", "headers": [(b"x-real-ip", b"1.2.3.4")], "client": ("127.0.0.1", 0)})
    response = Response()

    with pytest.raises(TooManyAttempts):
        await service.login(request, response, SLogin(email="a@b.com", password="pwd"))
    assert cache.set_called is True


@pytest.mark.asyncio
async def test_auth_refresh_invalid_token(monkeypatch):
    service = AuthBusinessService()
    service.user_service = types.SimpleNamespace()
    monkeypatch.setattr("app.services.business.auth.verify_token", lambda token: (_ for _ in ()).throw(JWTError()))
    request = Request({"type": "http", "headers": [], "client": ("127.0.0.1", 0)})
    request._cookies = {"refresh_token": create_refresh_token(SRefreshToken(sub="1").model_dump())}

    with pytest.raises(UnauthorizedException):
        await service.refresh(request, Response())


# ---------------- User service ----------------


@pytest.mark.asyncio
async def test_user_login_wrong_password(monkeypatch, db_session):
    service = UserService(db_session)
    user = types.SimpleNamespace(hashed_password="hashed")

    async def fake_get(**kwargs):
        return user

    monkeypatch.setattr(service, "get_first_by_filters", fake_get)
    monkeypatch.setattr("app.services.user.verify_password", lambda plain_password, hashed_password: False)

    with pytest.raises(UnauthorizedException):
        await service.login(SLogin(email="x@y.z", password="bad"))


@pytest.mark.asyncio
async def test_create_user_conflict_prioritizes_email(monkeypatch, db_session):
    service = UserService(db_session)

    async def fail_create(**kwargs):
        raise IntegrityError("stmt", "params", Exception("users_email_key username"))

    monkeypatch.setattr(service, "create", fail_create)

    with pytest.raises(EmailAlreadyTaken):
        await service.create_user(
            SRegister(  # type: ignore[name-defined]
                first_name="a",
                second_name="b",
                email="x@y.z",
                username="user",
                password="pass",
            )
        )


# ---------------- Booking/Payment services ----------------


@pytest.mark.asyncio
async def test_booking_cancel_conflict(monkeypatch, db_session):
    service = BookingService(db_session)
    repo = types.SimpleNamespace()
    async def check_status(**kwargs):
        return BookingStatus.PAID
    repo.check_booking_status = check_status
    repo.cancel_booking = lambda **kwargs: (_ for _ in ()).throw(AssertionError("should not cancel"))
    monkeypatch.setattr(service, "_repository", repo, raising=False)

    with pytest.raises(ConflictException):
        await service.cancel_booking(1, 1, False)


@pytest.mark.asyncio
async def test_booking_with_timeslots_not_found(monkeypatch, db_session):
    service = BookingService(db_session)
    repo = types.SimpleNamespace()

    async def fail(*args, **kwargs):
        raise NoResultFound

    repo.get_booking_with_timeslots_by_id = fail
    monkeypatch.setattr(service, "_repository", repo, raising=False)

    with pytest.raises(NotFoundException):
        await service.get_booking_with_timeslots_by_id(1, 1, False)


@pytest.mark.asyncio
async def test_payment_create_non_owner(monkeypatch):
    service = PaymentBusinessService(token_data=SAccessToken(sub="1", admin=False))
    booking = types.SimpleNamespace(user_id=2)
    async def get_booking(booking_id):
        return booking
    service.booking_service = types.SimpleNamespace(get_one_by_id=get_booking)
    service.payment_service = types.SimpleNamespace()

    with pytest.raises(BookingNotFound):
        await service.create_payment(10)


@pytest.mark.asyncio
async def test_payment_confirm_not_found(monkeypatch):
    service = PaymentBusinessService(token_data=SAccessToken(sub="1", admin=False))

    async def raise_not_found(payment_id):
        raise NotFoundException("not found")

    service.payment_service = types.SimpleNamespace(get_one_by_id=raise_not_found)
    service.booking_service = types.SimpleNamespace()

    with pytest.raises(PaymentNotFound):
        await service.confirm_payment(5)


@pytest.mark.asyncio
async def test_payment_confirm_wrong_user(monkeypatch):
    service = PaymentBusinessService(token_data=SAccessToken(sub="1", admin=False))

    async def get_payment(payment_id):
        return Payment(booking_id=99, external_id="ext")

    async def get_booking(booking_id):
        return Booking(
            user_id=2,
            room_id=1,
            timeslot_id=1,
            status=BookingStatus.PENDING_PAYMENTS,
            total_price=Decimal("0"),
            paid_at=None,
            canceled_at=None,
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=30),
        )

    service.payment_service = types.SimpleNamespace(get_one_by_id=get_payment, update_by_id=lambda *a, **k: None)
    service.booking_service = types.SimpleNamespace(get_one_by_id=get_booking, set_booking_paid=lambda *_: None)

    with pytest.raises(PaymentNotFound):
        await service.confirm_payment(1)


# ---------------- Cache keys ----------------


def test_cache_keys_formats():
    dt_from = datetime(2020, 1, 1, 12, 0, 0)
    dt_to = datetime(2020, 1, 2, 13, 0, 0)

    assert keys.login_ip(None) == "login:None"
    assert keys.locations_all() == "locations:all"
    assert "2020-01-01T12:00:00" in keys.timeslots_by_room_and_range(1, dt_from, dt_to)
    assert keys.timeslots_room_prefix(5) == "timeslots:5:*"
