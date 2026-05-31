import pytest

from app.config import settings
from app.integrations.payment_gateway import PaymentGatewayUnavailableError
from app.overload import overload_controller
from app.schemas.auth import SAccessToken
from app.services.business.payments import PaymentBusinessService
from app.utils.err.payment import PaymentProviderUnavailable


@pytest.fixture(autouse=True)
def reset_overload_controller():
    overload_controller.reset()
    yield
    overload_controller.reset()


@pytest.mark.asyncio
@pytest.mark.failure
@pytest.mark.unit
async def test__payment_gateway_failure__marks_dependency_degraded(monkeypatch):
    monkeypatch.setattr(settings, "PAYMENT_RETRY_MAX_ATTEMPTS", 1)
    service = PaymentBusinessService(token_data=SAccessToken(sub="1", admin=False))

    async def failing_gateway_call():
        raise PaymentGatewayUnavailableError("down")

    with pytest.raises(PaymentProviderUnavailable):
        await service._call_gateway_with_retry("confirm_payment", failing_gateway_call)

    snapshot = overload_controller.snapshot()
    assert snapshot["status"] == "degraded"
    assert snapshot["degraded_components"] == [
        {"component": "payment_gateway", "reason": "retry_exhausted"}
    ]
