import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.api.routers import system as system_router
from app.overload import overload_controller


@pytest.fixture(autouse=True)
def reset_overload_controller():
    overload_controller.reset()
    yield
    overload_controller.reset()


@pytest.mark.asyncio
@pytest.mark.unit
async def test__degradation_endpoint__reports_degraded_components():
    app = FastAPI()
    app.include_router(system_router.router)
    overload_controller.mark_dependency_degraded("payment_gateway", "retry_exhausted")

    transport = ASGITransport(app=app, raise_app_exceptions=True)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/degradation")

    assert response.status_code == 200
    assert response.json()["status"] == "degraded"
    assert response.json()["degraded_components"] == [
        {"component": "payment_gateway", "reason": "retry_exhausted"}
    ]


@pytest.mark.asyncio
@pytest.mark.unit
async def test__ready__reflects_partial_degradation_but_health_stays_available(monkeypatch):
    async def always_true():
        return True

    monkeypatch.setattr(system_router, "_check_db", always_true)
    monkeypatch.setattr(system_router, "_check_redis", always_true)
    monkeypatch.setattr(system_router, "_check_rabbitmq", always_true)

    app = FastAPI()
    app.include_router(system_router.router)
    overload_controller.mark_dependency_degraded("payment_gateway", "retry_exhausted")

    transport = ASGITransport(app=app, raise_app_exceptions=True)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        ready_response = await client.get("/ready")
        health_response = await client.get("/health")

    assert ready_response.status_code == 503
    assert ready_response.json()["status"] == "degraded"
    assert ready_response.json()["degradation"]["status"] == "degraded"
    assert health_response.status_code == 200
    assert health_response.json()["status"] == "ok"
