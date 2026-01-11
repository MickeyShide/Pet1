import pytest

from app.schemas.auth import SAccessToken, SRefreshToken
from app.utils.security import create_refresh_token
from tests.factories import create_user
from tests.integration.api.helpers import clear_overrides, override_token


@pytest.mark.asyncio
async def test__register_creates_user(async_client, db_session, faker):
    payload = {
        "first_name": faker.first_name(),
        "second_name": faker.last_name(),
        "email": faker.unique.email(),
        "username": faker.unique.user_name(),
        "password": "StrongPassword123!",
    }

    response = await async_client.post("/auth/register", json=payload)

    assert response.status_code == 201, response.text
    data = response.json()
    assert data["email"] == payload["email"]
    assert data["username"] == payload["username"]


@pytest.mark.asyncio
async def test__register_duplicate_email_returns_conflict(async_client, db_session, faker):
    payload = {
        "first_name": faker.first_name(),
        "second_name": faker.last_name(),
        "email": faker.unique.email(),
        "username": faker.unique.user_name(),
        "password": "StrongPassword123!",
    }

    first = await async_client.post("/auth/register", json=payload)
    assert first.status_code == 201

    response = await async_client.post("/auth/register", json=payload)

    assert response.status_code == 409


@pytest.mark.asyncio
async def test__register_duplicate_username_returns_conflict(async_client, db_session, faker):
    base_username = faker.unique.user_name()
    payload = {
        "first_name": faker.first_name(),
        "second_name": faker.last_name(),
        "email": faker.unique.email(),
        "username": base_username,
        "password": "StrongPassword123!",
    }
    first = await async_client.post("/auth/register", json=payload)
    assert first.status_code == 201

    second_payload = {
        "first_name": faker.first_name(),
        "second_name": faker.last_name(),
        "email": faker.unique.email(),
        "username": base_username,
        "password": "StrongPassword123!",
    }

    response = await async_client.post("/auth/register", json=second_payload)

    assert response.status_code == 409, response.text


@pytest.mark.asyncio
async def test__register_invalid_email_returns_422(async_client, faker):
    payload = {
        "first_name": faker.first_name(),
        "second_name": faker.last_name(),
        "email": "not-an-email",
        "username": faker.unique.user_name(),
        "password": "StrongPassword123!",
    }

    response = await async_client.post("/auth/register", json=payload)

    assert response.status_code == 422, response.text


@pytest.mark.asyncio
async def test__register_missing_email_returns_422(async_client, faker):
    payload = {
        "first_name": faker.first_name(),
        "second_name": faker.last_name(),
        "username": faker.unique.user_name(),
        "password": "StrongPassword123!",
    }

    response = await async_client.post("/auth/register", json=payload)

    assert response.status_code == 422, response.text


@pytest.mark.asyncio
async def test__register_missing_password_returns_422(async_client, faker):
    payload = {
        "first_name": faker.first_name(),
        "second_name": faker.last_name(),
        "email": faker.unique.email(),
        "username": faker.unique.user_name(),
    }

    response = await async_client.post("/auth/register", json=payload)

    assert response.status_code == 422, response.text


@pytest.mark.asyncio
async def test__register_extra_field_returns_422(async_client, faker):
    payload = {
        "first_name": faker.first_name(),
        "second_name": faker.last_name(),
        "email": faker.unique.email(),
        "username": faker.unique.user_name(),
        "password": "StrongPassword123!",
        "extra": "value",
    }

    response = await async_client.post("/auth/register", json=payload)

    assert response.status_code == 422, response.text


@pytest.mark.asyncio
async def test__login_returns_token(async_client, db_session, faker):
    password = "ValidPass123!"
    payload = {
        "first_name": faker.first_name(),
        "second_name": faker.last_name(),
        "email": faker.unique.email(),
        "username": faker.unique.user_name(),
        "password": password,
    }
    register_response = await async_client.post("/auth/register", json=payload)
    assert register_response.status_code == 201

    response = await async_client.post(
        "/auth/login",
        json={"email": payload["email"], "password": password},
    )

    assert response.status_code == 200, response.text
    data = response.json()
    assert "access_token" in data
    cookie_header = response.headers.get("set-cookie")
    assert cookie_header and "refresh_token=" in cookie_header


@pytest.mark.asyncio
async def test__login_missing_email_returns_422(async_client):
    response = await async_client.post("/auth/login", json={"password": "pass"})

    assert response.status_code == 422, response.text


@pytest.mark.asyncio
async def test__login_missing_password_returns_422(async_client):
    response = await async_client.post("/auth/login", json={"email": "user@example.com"})

    assert response.status_code == 422, response.text


@pytest.mark.asyncio
async def test__login_invalid_email_returns_422(async_client):
    response = await async_client.post(
        "/auth/login", json={"email": "not-an-email", "password": "pass"}
    )

    assert response.status_code == 422, response.text


@pytest.mark.asyncio
async def test__login_wrong_password_returns_unauthorized(async_client, db_session, faker):
    password = "ValidPass123!"
    payload = {
        "first_name": faker.first_name(),
        "second_name": faker.last_name(),
        "email": faker.unique.email(),
        "username": faker.unique.user_name(),
        "password": password,
    }
    register_response = await async_client.post("/auth/register", json=payload)
    assert register_response.status_code == 201

    response = await async_client.post(
        "/auth/login",
        json={"email": payload["email"], "password": "WrongPassword!"},
    )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test__login_unknown_email_returns_unauthorized(async_client, db_session, faker):
    payload = {
        "email": faker.unique.email(),
        "password": "SomePassword123!",
    }

    response = await async_client.post("/auth/login", json=payload)

    assert response.status_code == 401, response.text


@pytest.mark.asyncio
async def test__refresh_without_cookie_returns_unauthorized(async_client):
    response = await async_client.post("/auth/refresh")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test__refresh_with_invalid_cookie_returns_unauthorized(async_client):
    async_client.cookies.set("refresh_token", "invalid")
    response = await async_client.post("/auth/refresh")
    async_client.cookies.clear()
    assert response.status_code == 401


@pytest.mark.asyncio
async def test__refresh_with_unknown_user_returns_unauthorized(async_client):
    refresh_cookie = create_refresh_token(SRefreshToken(sub="9999").model_dump())
    async_client.cookies.set("refresh_token", refresh_cookie)

    response = await async_client.post("/auth/refresh")

    async_client.cookies.clear()
    assert response.status_code == 401, response.text


@pytest.mark.asyncio
async def test__refresh_with_valid_cookie_returns_token(async_client, db_session, faker):
    user = await create_user(db_session, faker)
    await db_session.flush()
    refresh_cookie = create_refresh_token(SRefreshToken(sub=str(user.id)).model_dump())
    async_client.cookies.set("refresh_token", refresh_cookie)

    response = await async_client.post("/auth/refresh")

    async_client.cookies.clear()
    assert response.status_code == 200, response.text
    assert "access_token" in response.json()
    cookie_header = response.headers.get("set-cookie")
    assert cookie_header and "refresh_token=" in cookie_header


@pytest.mark.asyncio
async def test__get_me_requires_auth(async_client):
    response = await async_client.get("/auth/me", headers={"Authorization": "Bearer invalid"})
    assert response.status_code == 401


@pytest.mark.asyncio
async def test__get_me_returns_current_user(async_client, db_session, faker):
    user = await create_user(db_session, faker)
    await db_session.flush()
    token = SAccessToken(sub=str(user.id), admin=False)
    override_token(async_client.app_ref, token)

    response = await async_client.get("/auth/me", headers={"Authorization": "Bearer stub"})

    clear_overrides(async_client.app_ref)
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["email"] == user.email


@pytest.mark.asyncio
async def test__login_rate_limited_returns_429(async_client, monkeypatch):
    import app.services.user as user_module

    async def _fake_try_get(self, key, default=None):
        return 5

    async def _fake_try_set(self, key, value, ttl=None):
        return None

    monkeypatch.setattr(user_module.CacheService, "try_get", _fake_try_get)
    monkeypatch.setattr(user_module.CacheService, "try_set", _fake_try_set)

    response = await async_client.post(
        "/auth/login",
        json={"email": "user@example.com", "password": "pass"},
    )

    assert response.status_code == 429, response.text
