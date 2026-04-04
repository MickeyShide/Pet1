import asyncio

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.graceful_shutdown import (
    GracefulShutdownMiddleware,
    get_graceful_shutdown_state,
    install_graceful_shutdown,
)


def test_install_graceful_shutdown_adds_state_and_middleware():
    app = FastAPI()

    install_graceful_shutdown(app, retry_after_seconds=9)

    state = get_graceful_shutdown_state(app)

    assert state.is_draining is False
    assert any(middleware.cls is GracefulShutdownMiddleware for middleware in app.user_middleware)


@pytest.mark.asyncio
async def test_draining_rejects_new_write_requests():
    app = FastAPI()
    calls = {"count": 0}
    install_graceful_shutdown(app, retry_after_seconds=9)

    @app.post("/mutate")
    async def mutate():
        calls["count"] += 1
        return {"ok": True}

    get_graceful_shutdown_state(app).begin_draining("test")

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        response = await client.post("/mutate")

    assert response.status_code == 503
    assert response.headers["Retry-After"] == "9"
    assert calls["count"] == 0


@pytest.mark.asyncio
async def test_inflight_request_finishes_after_draining_starts():
    app = FastAPI()
    install_graceful_shutdown(app, retry_after_seconds=9)
    started = asyncio.Event()
    proceed = asyncio.Event()
    calls = {"count": 0}

    @app.post("/mutate")
    async def mutate():
        started.set()
        await proceed.wait()
        calls["count"] += 1
        return {"ok": True}

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        first_request = asyncio.create_task(client.post("/mutate"))
        await started.wait()

        get_graceful_shutdown_state(app).begin_draining("test")
        proceed.set()

        first_response = await first_request
        second_response = await client.post("/mutate")

    assert first_response.status_code == 200
    assert second_response.status_code == 503
    assert calls["count"] == 1
