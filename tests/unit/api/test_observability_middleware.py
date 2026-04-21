import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.observability.middleware import RequestObservabilityMiddleware


@pytest.mark.asyncio
async def test__observability_middleware_generates_request_id_header():
    app = FastAPI()
    app.add_middleware(RequestObservabilityMiddleware)

    @app.get("/ping")
    async def ping():
        return {"ok": True}

    transport = ASGITransport(app=app, raise_app_exceptions=True)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/ping")

    # Auto id.
    assert response.status_code == 200
    assert response.headers.get("X-Request-ID")


@pytest.mark.asyncio
async def test__observability_middleware_keeps_incoming_request_id():
    app = FastAPI()
    app.add_middleware(RequestObservabilityMiddleware)

    @app.get("/ping")
    async def ping():
        return {"ok": True}

    transport = ASGITransport(app=app, raise_app_exceptions=True)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/ping", headers={"X-Request-ID": "req-123"})

    # Keep caller id.
    assert response.status_code == 200
    assert response.headers.get("X-Request-ID") == "req-123"
