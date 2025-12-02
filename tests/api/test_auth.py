import pytest

from app.api import deps
from app.schemas.auth import SAccessToken, SRefreshToken
from app.utils.security import create_refresh_token
from tests.fixtures.factories import create_user


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

    # ❗BUG FOUND: ожидался 401, но сервис возвращает 404, раскрывая наличие пользователей.
    assert response.status_code == 401, response.text


def override_token(app, token: SAccessToken):
    async def fake_dep(jwt_token: deps.HTTPBearerDepends):
        return token

    app.dependency_overrides[deps.get_token_data] = fake_dep
    app.dependency_overrides[deps.get_admin_token_data] = fake_dep


@pytest.mark.asyncio
async def test__refresh_without_cookie_returns_unauthorized(async_client):
    response = await async_client.post("/auth/refresh")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test__refresh_with_valid_cookie_returns_token(async_client, db_session, faker):
    user = await create_user(db_session, faker)
    await db_session.commit()
    refresh_cookie = create_refresh_token(SRefreshToken(sub=str(user.id)).model_dump())
    async_client.cookies.set("refresh_token", refresh_cookie)

    response = await async_client.post("/auth/refresh")

    async_client.cookies.clear()
    assert response.status_code == 200, response.text
    assert "access_token" in response.json()


@pytest.mark.asyncio
async def test__get_me_requires_auth(async_client):
    response = await async_client.get("/auth/me", headers={"Authorization": "Bearer invalid"})
    assert response.status_code == 401


@pytest.mark.asyncio
async def test__get_me_returns_current_user(async_client, db_session, faker):
    user = await create_user(db_session, faker)
    await db_session.commit()
    token = SAccessToken(sub=str(user.id), admin=False)
    override_token(async_client.app_ref, token)

    response = await async_client.get("/auth/me", headers={"Authorization": "Bearer stub"})

    async_client.app_ref.dependency_overrides.clear()
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["email"] == user.email
