import asyncio

import pytest
from starlette import status

from app.config import settings
from app.overload import OverloadRejected, overload_controller, overload_guard


@pytest.fixture(autouse=True)
def reset_overload_controller():
    overload_controller.reset()
    yield
    overload_controller.reset()


@pytest.mark.asyncio
@pytest.mark.unit
async def test__overload_guard__rejects_when_max_active_is_reached(monkeypatch):
    monkeypatch.setattr(settings, "OVERLOAD_BOOKING_CREATE_MAX_ACTIVE", 1)
    monkeypatch.setattr(settings, "OVERLOAD_BOOKING_CREATE_RATE_LIMIT", 100)

    async with overload_guard("booking_create"):
        with pytest.raises(OverloadRejected) as exc_info:
            async with overload_guard("booking_create"):
                pass

    assert exc_info.value.status_code == status.HTTP_429_TOO_MANY_REQUESTS
    assert exc_info.value.detail["error_code"] == "too_many_active_operations"


@pytest.mark.asyncio
@pytest.mark.unit
async def test__overload_guard__rejects_when_rate_limit_is_exceeded(monkeypatch):
    monkeypatch.setattr(settings, "OVERLOAD_BOOKING_CREATE_MAX_ACTIVE", 10)
    monkeypatch.setattr(settings, "OVERLOAD_BOOKING_CREATE_RATE_LIMIT", 1)
    monkeypatch.setattr(settings, "OVERLOAD_RATE_WINDOW_SECONDS", 60.0)

    async with overload_guard("booking_create"):
        pass

    with pytest.raises(OverloadRejected) as exc_info:
        async with overload_guard("booking_create"):
            pass

    assert exc_info.value.status_code == status.HTTP_429_TOO_MANY_REQUESTS
    assert exc_info.value.detail["error_code"] == "rate_limit_exceeded"
    assert exc_info.value.detail["retry_after"] == settings.OVERLOAD_RETRY_AFTER_SECONDS


@pytest.mark.asyncio
@pytest.mark.unit
async def test__overload_guard__rejects_degraded_payment_dependency():
    overload_controller.mark_dependency_degraded("payment_gateway", "test")

    with pytest.raises(OverloadRejected) as exc_info:
        async with overload_guard("payment_create"):
            pass

    assert exc_info.value.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
    assert exc_info.value.detail["error_code"] == "dependency_degraded"
    assert exc_info.value.detail["degraded_component"] == "payment_gateway"


@pytest.mark.asyncio
@pytest.mark.unit
async def test__overload_guard__rejects_high_queue_pressure(monkeypatch):
    monkeypatch.setattr(settings, "OVERLOAD_MAX_QUEUE_PRESSURE", 1)
    overload_controller.set_queue_pressure("background_task_schedule", 1)

    with pytest.raises(OverloadRejected) as exc_info:
        async with overload_guard("background_task_schedule"):
            pass

    assert exc_info.value.status_code == status.HTTP_429_TOO_MANY_REQUESTS
    assert exc_info.value.detail["error_code"] == "queue_pressure_high"


@pytest.mark.asyncio
@pytest.mark.unit
async def test__overload_guard__turns_timeout_into_stable_response(monkeypatch):
    monkeypatch.setattr(settings, "OVERLOAD_PAYMENT_TIMEOUT_SECONDS", 0.01)

    with pytest.raises(OverloadRejected) as exc_info:
        async with overload_guard("payment_create"):
            await asyncio.sleep(0.05)

    assert exc_info.value.status_code == status.HTTP_504_GATEWAY_TIMEOUT
    assert exc_info.value.detail["error_code"] == "operation_timeout"
