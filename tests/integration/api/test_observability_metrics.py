import pytest


@pytest.mark.asyncio
async def test__metrics_endpoint_exposes_prometheus_metrics(async_client):
    response = await async_client.get("/metrics")

    # Basic scrape.
    assert response.status_code == 200
    assert "http_requests_total" in response.text
    assert "http_request_duration_seconds" in response.text
    assert "booking_conflicts_total" in response.text
    assert "idempotency_reuse_total" in response.text
