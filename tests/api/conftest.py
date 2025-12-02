import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import AsyncClient, ASGITransport

from app.api import routers


@pytest.fixture(scope="session")
def fastapi_app():
    app = FastAPI(title="test-app")
    for router in routers.__all__:
        app.include_router(router)
    return app


@pytest_asyncio.fixture
async def async_client(fastapi_app):
    transport = ASGITransport(app=fastapi_app, raise_app_exceptions=True)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        client.app_ref = fastapi_app
        yield client
