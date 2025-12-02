from starlette.requests import Request
from starlette.responses import Response
from sqlalchemy import select
import pytest

from app.models import User
from app.schemas.auth import (
    SRegister,
    SLogin,
    SAccessToken,
    SRefreshToken,
)
from app.services.business.auth import AuthBusinessService
from app.utils.err.base.unauthorized import UnauthorizedException
from app.utils.security import create_refresh_token
from tests.fixtures.factories import create_user


def _make_request_with_cookie(cookie_value: str | None) -> Request:
    headers = []
    if cookie_value is not None:
        headers.append(
            (b"cookie", f"refresh_token={cookie_value}".encode("latin-1"))
        )
    return Request({"type": "http", "headers": headers})


@pytest.mark.asyncio
async def test__register__creates_user_and_hashes_password(db_session, faker):
    # Given
    service = AuthBusinessService()
    payload = SRegister(
        first_name=faker.first_name(),
        second_name=faker.last_name(),
        email=faker.unique.email(),
        username=faker.unique.user_name(),
        password="StrongPass123!",
    )

    # When
    result = await service.register(payload)

    # Then
    assert result.email == payload.email
    stored = (
        await db_session.execute(select(User).where(User.email == payload.email))
    ).scalar_one()
    assert stored.hashed_password != payload.password


@pytest.mark.asyncio
async def test__login__returns_access_token_and_sets_cookie(db_session, faker):
    # Given
    service = AuthBusinessService()
    payload = SRegister(
        first_name=faker.first_name(),
        second_name=faker.last_name(),
        email=faker.unique.email(),
        username=faker.unique.user_name(),
        password="ValidPass123!",
    )
    await service.register(payload)
    response = Response()

    # When
    token_out = await service.login(
        response,
        SLogin(email=payload.email, password=payload.password),
    )

    # Then
    assert token_out.access_token
    cookie_header = response.headers.get("set-cookie")
    assert cookie_header and "refresh_token=" in cookie_header


@pytest.mark.asyncio
async def test__refresh__without_cookie_raises(db_session):
    # Given
    service = AuthBusinessService()
    request = _make_request_with_cookie(None)
    response = Response()

    # When / Then
    with pytest.raises(UnauthorizedException):
        await service.refresh(request, response)


@pytest.mark.asyncio
async def test__refresh__invalid_token_raises(db_session):
    # Given
    service = AuthBusinessService()
    request = _make_request_with_cookie("invalid")
    response = Response()

    # When / Then
    with pytest.raises(UnauthorizedException):
        await service.refresh(request, response)


@pytest.mark.asyncio
async def test__refresh__valid_cookie_returns_new_access_token(db_session, faker):
    # Given
    user = await create_user(db_session, faker)
    await db_session.commit()
    service = AuthBusinessService()
    refresh_token = create_refresh_token(SRefreshToken(sub=str(user.id)).model_dump())
    request = _make_request_with_cookie(refresh_token)
    response = Response()

    # When
    token_out = await service.refresh(request, response)

    # Then
    assert token_out.access_token
    cookie_header = response.headers.get("set-cookie")
    assert cookie_header and "refresh_token=" in cookie_header


@pytest.mark.asyncio
async def test__get_me__returns_current_user(db_session, faker):
    # Given
    user = await create_user(db_session, faker)
    await db_session.commit()
    token = SAccessToken(sub=str(user.id), admin=False)
    service = AuthBusinessService(token_data=token)

    # When
    result = await service.get_me()

    # Then
    assert result.email == user.email
