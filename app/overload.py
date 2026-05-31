from __future__ import annotations

import asyncio
from collections import defaultdict, deque
from contextlib import asynccontextmanager
from dataclasses import dataclass
from functools import wraps
from time import monotonic
from typing import Any, AsyncIterator, Awaitable, Callable, TypeVar

from starlette import status
from starlette.exceptions import HTTPException

from app.config import settings

RT = TypeVar("RT")


@dataclass(frozen=True)
class OperationLimit:
    max_active: int
    rate_limit: int
    rate_window_seconds: float
    timeout_seconds: float


class OverloadRejected(HTTPException):
    def __init__(
        self,
        *,
        status_code: int,
        error_code: str,
        message: str,
        retry_after: int | None = None,
        degraded_component: str | None = None,
    ) -> None:
        detail: dict[str, object] = {
            "error_code": error_code,
            "message": message,
        }
        if retry_after is not None:
            detail["retry_after"] = retry_after
        if degraded_component is not None:
            detail["degraded_component"] = degraded_component

        headers = {"Retry-After": str(retry_after)} if retry_after is not None else None
        super().__init__(status_code=status_code, detail=detail, headers=headers)


class OverloadController:
    def __init__(self) -> None:
        self._active: dict[str, int] = defaultdict(int)
        self._request_times: dict[str, deque[float]] = defaultdict(deque)
        self._queue_pressure: dict[str, int] = defaultdict(int)
        self._degraded_components: dict[str, str] = {}
        self._lock = asyncio.Lock()

    def reset(self) -> None:
        self._active.clear()
        self._request_times.clear()
        self._queue_pressure.clear()
        self._degraded_components.clear()

    def mark_dependency_degraded(self, component: str, reason: str = "dependency_unavailable") -> None:
        self._degraded_components[component] = reason

    def clear_dependency_degraded(self, component: str) -> None:
        self._degraded_components.pop(component, None)

    def set_queue_pressure(self, operation: str, pressure: int) -> None:
        self._queue_pressure[operation] = max(0, pressure)

    def snapshot(self) -> dict[str, object]:
        degraded = [
            {"component": component, "reason": reason}
            for component, reason in sorted(self._degraded_components.items())
        ]
        return {
            "status": "degraded" if degraded else "ok",
            "active_operations": dict(self._active),
            "queue_pressure": dict(self._queue_pressure),
            "degraded_components": degraded,
        }

    def is_degraded(self) -> bool:
        return bool(self._degraded_components)

    def _limit_for(self, operation: str) -> OperationLimit:
        common_rate_window = settings.OVERLOAD_RATE_WINDOW_SECONDS
        if operation.startswith("booking_create"):
            return OperationLimit(
                max_active=settings.OVERLOAD_BOOKING_CREATE_MAX_ACTIVE,
                rate_limit=settings.OVERLOAD_BOOKING_CREATE_RATE_LIMIT,
                rate_window_seconds=common_rate_window,
                timeout_seconds=settings.OVERLOAD_BOOKING_CREATE_TIMEOUT_SECONDS,
            )
        if operation.startswith("payment"):
            return OperationLimit(
                max_active=settings.OVERLOAD_PAYMENT_MAX_ACTIVE,
                rate_limit=settings.OVERLOAD_PAYMENT_RATE_LIMIT,
                rate_window_seconds=common_rate_window,
                timeout_seconds=settings.OVERLOAD_PAYMENT_TIMEOUT_SECONDS,
            )
        if operation.startswith("file_upload"):
            return OperationLimit(
                max_active=settings.OVERLOAD_FILE_UPLOAD_MAX_ACTIVE,
                rate_limit=settings.OVERLOAD_FILE_UPLOAD_RATE_LIMIT,
                rate_window_seconds=common_rate_window,
                timeout_seconds=settings.OVERLOAD_FILE_UPLOAD_TIMEOUT_SECONDS,
            )
        return OperationLimit(
            max_active=settings.OVERLOAD_BACKGROUND_TASK_MAX_ACTIVE,
            rate_limit=settings.OVERLOAD_BACKGROUND_TASK_RATE_LIMIT,
            rate_window_seconds=common_rate_window,
            timeout_seconds=settings.OVERLOAD_BACKGROUND_TASK_TIMEOUT_SECONDS,
        )

    def _reject_if_degraded(self, operation: str) -> None:
        component_by_operation = {
            "payment": "payment_gateway",
            "background_task": "rabbitmq",
            "file_upload": "minio",
        }
        for prefix, component in component_by_operation.items():
            if operation.startswith(prefix) and component in self._degraded_components:
                raise OverloadRejected(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    error_code="dependency_degraded",
                    message=f"{component} is degraded",
                    retry_after=settings.OVERLOAD_RETRY_AFTER_SECONDS,
                    degraded_component=component,
                )

    async def enter(self, operation: str) -> OperationLimit:
        limit = self._limit_for(operation)
        now = monotonic()

        async with self._lock:
            self._reject_if_degraded(operation)

            timestamps = self._request_times[operation]
            while timestamps and now - timestamps[0] >= limit.rate_window_seconds:
                timestamps.popleft()

            if limit.rate_limit > 0 and len(timestamps) >= limit.rate_limit:
                raise OverloadRejected(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    error_code="rate_limit_exceeded",
                    message=f"Rate limit exceeded for {operation}",
                    retry_after=settings.OVERLOAD_RETRY_AFTER_SECONDS,
                )

            if limit.max_active > 0 and self._active[operation] >= limit.max_active:
                raise OverloadRejected(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    error_code="too_many_active_operations",
                    message=f"Too many active operations for {operation}",
                    retry_after=settings.OVERLOAD_RETRY_AFTER_SECONDS,
                )

            if self._queue_pressure[operation] >= settings.OVERLOAD_MAX_QUEUE_PRESSURE:
                raise OverloadRejected(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    error_code="queue_pressure_high",
                    message=f"Queue pressure is too high for {operation}",
                    retry_after=settings.OVERLOAD_RETRY_AFTER_SECONDS,
                )

            timestamps.append(now)
            self._active[operation] += 1
            return limit

    async def exit(self, operation: str) -> None:
        async with self._lock:
            if self._active[operation] > 0:
                self._active[operation] -= 1


overload_controller = OverloadController()


@asynccontextmanager
async def overload_guard(operation: str) -> AsyncIterator[None]:
    limit = await overload_controller.enter(operation)
    try:
        async with asyncio.timeout(limit.timeout_seconds):
            yield
    except TimeoutError as exc:
        raise OverloadRejected(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            error_code="operation_timeout",
            message=f"Operation {operation} timed out",
            retry_after=settings.OVERLOAD_RETRY_AFTER_SECONDS,
        ) from exc
    finally:
        await overload_controller.exit(operation)


def overload_protected(operation: str) -> Callable[[Callable[..., Awaitable[RT]]], Callable[..., Awaitable[RT]]]:
    def decorator(func: Callable[..., Awaitable[RT]]) -> Callable[..., Awaitable[RT]]:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> RT:
            async with overload_guard(operation):
                return await func(*args, **kwargs)

        return wrapper

    return decorator
