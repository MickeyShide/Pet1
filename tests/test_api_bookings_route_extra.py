import pytest

from app.api.routers import bookings
from app.schemas.auth import SAccessToken


@pytest.mark.asyncio
async def test_create_payment_route_delegates_to_business_service(monkeypatch):
    called = {}

    async def fake_create_payment(self, booking_id: int):
        called["booking_id"] = booking_id
        return {"paid": True}

    monkeypatch.setattr(bookings.PaymentBusinessService, "create_payment", fake_create_payment)

    token = SAccessToken(sub="1", admin=False)
    result = await bookings.create_payment_route(token, 123)

    assert result == {"paid": True}
    assert called["booking_id"] == 123
