import pytest

from app.integrations.payment_gateway import (
    PaymentGatewayDeclinedError,
    PaymentGatewayRetryableError,
    PaymentGatewayTimeoutError,
    retry_with_backoff,
)


@pytest.mark.asyncio
async def test_retry_with_backoff_retries_retryable_and_grows_delay():
    attempts = {"count": 0}
    sleep_calls: list[float] = []

    async def operation():
        attempts["count"] += 1
        if attempts["count"] < 3:
            raise PaymentGatewayTimeoutError("timeout")
        return "ok"

    async def fake_sleep(delay: float):
        sleep_calls.append(delay)

    result = await retry_with_backoff(
        operation,
        max_attempts=4,
        base_delay_seconds=0.1,
        max_delay_seconds=1.0,
        is_retryable=lambda exc: isinstance(exc, PaymentGatewayRetryableError),
        sleep=fake_sleep,
    )

    assert result == "ok"
    assert attempts["count"] == 3
    assert sleep_calls == [0.1, 0.2]


@pytest.mark.asyncio
async def test_retry_with_backoff_does_not_retry_non_retryable():
    attempts = {"count": 0}

    async def operation():
        attempts["count"] += 1
        raise PaymentGatewayDeclinedError("declined")

    with pytest.raises(PaymentGatewayDeclinedError):
        await retry_with_backoff(
            operation,
            max_attempts=5,
            base_delay_seconds=0.1,
            max_delay_seconds=1.0,
            is_retryable=lambda exc: isinstance(exc, PaymentGatewayRetryableError),
        )

    assert attempts["count"] == 1


@pytest.mark.asyncio
async def test_retry_with_backoff_raises_after_max_attempts():
    attempts = {"count": 0}
    sleep_calls: list[float] = []

    async def operation():
        attempts["count"] += 1
        raise PaymentGatewayTimeoutError("timeout")

    async def fake_sleep(delay: float):
        sleep_calls.append(delay)

    with pytest.raises(PaymentGatewayTimeoutError):
        await retry_with_backoff(
            operation,
            max_attempts=3,
            base_delay_seconds=0.1,
            max_delay_seconds=1.0,
            is_retryable=lambda exc: isinstance(exc, PaymentGatewayRetryableError),
            sleep=fake_sleep,
        )

    assert attempts["count"] == 3
    assert sleep_calls == [0.1, 0.2]
