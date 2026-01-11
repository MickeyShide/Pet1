import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.api import routers
from app.schemas.auth import SAccessToken
from tests.integration.api.helpers import clear_overrides, override_token


@pytest.fixture(scope="session")
def fastapi_app():
    app = FastAPI(title="test-app")
    for router in routers.__all__:
        app.include_router(router)
    return app


@pytest_asyncio.fixture
async def async_client(fastapi_app, db_session):
    transport = ASGITransport(app=fastapi_app, raise_app_exceptions=True)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        client.app_ref = fastapi_app
        clear_overrides(client.app_ref)
        yield client
        clear_overrides(client.app_ref)


@pytest_asyncio.fixture
async def authorized_client(async_client, user):
    token = SAccessToken(sub=str(user.id), admin=False)
    override_token(async_client.app_ref, token)
    yield async_client
    clear_overrides(async_client.app_ref)


@pytest_asyncio.fixture
async def admin_client(async_client, admin_user):
    token = SAccessToken(sub=str(admin_user.id), admin=True)
    override_token(async_client.app_ref, token)
    yield async_client
    clear_overrides(async_client.app_ref)
