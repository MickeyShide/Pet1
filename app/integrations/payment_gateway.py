from __future__ import annotations

import asyncio
from decimal import Decimal
from typing import Awaitable, Callable, TypeVar
from uuid import uuid4

T = TypeVar("T")


class PaymentGatewayError(Exception):
    pass


class PaymentGatewayRetryableError(PaymentGatewayError):
    pass


class PaymentGatewayNonRetryableError(PaymentGatewayError):
    pass


class PaymentGatewayTimeoutError(PaymentGatewayRetryableError):
    pass


class PaymentGatewayUnavailableError(PaymentGatewayRetryableError):
    pass


class PaymentGatewayRateLimitError(PaymentGatewayRetryableError):
    pass


class PaymentGatewayDeclinedError(PaymentGatewayNonRetryableError):
    pass


class PaymentGatewayInvalidRequestError(PaymentGatewayNonRetryableError):
    pass


class MockPaymentGateway:
    """
    Stub for an external payment provider.
    """

    async def create_payment(self, booking_id: int, amount: Decimal) -> str:
        if amount <= 0:
            raise PaymentGatewayInvalidRequestError("Payment amount must be greater than zero")
        return f"mock-{booking_id}-{uuid4().hex}"

    async def confirm_payment(self, external_id: str, amount: Decimal) -> None:
        if not external_id:
            raise PaymentGatewayInvalidRequestError("Missing payment external id")
        if amount <= 0:
            raise PaymentGatewayInvalidRequestError("Payment amount must be greater than zero")


async def retry_with_backoff(
    operation: Callable[[], Awaitable[T]],
    *,
    max_attempts: int,
    base_delay_seconds: float,
    max_delay_seconds: float,
    is_retryable: Callable[[Exception], bool],
    sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
) -> T:
    if max_attempts < 1:
        raise ValueError("max_attempts must be >= 1")

    attempt = 1
    while True:
        try:
            return await operation()
        except Exception as exc:
            if attempt >= max_attempts or not is_retryable(exc):
                raise

            delay = min(max_delay_seconds, base_delay_seconds * (2 ** (attempt - 1)))
            await sleep(max(0.0, delay))
            attempt += 1
