from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import AsyncIterator

from fastapi import FastAPI
from starlette import status
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send

STATE_KEY = "graceful_shutdown_state"
MUTATING_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})
# Ignore probe paths.
UNTRACKED_PATHS = frozenset({"/health", "/ready", "/metrics"})


class GracefulShutdownState:
    def __init__(self) -> None:
        self._draining = False
        self._active_requests = 0
        self._drain_reason: str | None = None
        self._drain_started_at: datetime | None = None
        self._idle = asyncio.Event()
        self._idle.set()
        self._lock = asyncio.Lock()

    @property
    def is_draining(self) -> bool:
        return self._draining

    @property
    def active_requests(self) -> int:
        return self._active_requests

    @property
    def drain_reason(self) -> str | None:
        return self._drain_reason

    @property
    def drain_started_at(self) -> datetime | None:
        return self._drain_started_at

    # начало шатдауна
    def begin_draining(self, reason: str = "shutdown") -> None:
        if self._draining:
            return
        self._draining = True
        self._drain_reason = reason
        self._drain_started_at = datetime.now(timezone.utc)

    # ждем пока запросы кончатся, но не больше timeout_seconds
    async def wait_for_active_requests(self, timeout_seconds: int) -> bool:
        if self._active_requests == 0:
            return True

        try:
            async with asyncio.timeout(timeout_seconds):
                await self._idle.wait() # ждет пока active requests == 0
            return True
        except TimeoutError:
            return False # даем инфу о том что что-то зависло/долго происходит

    # контекстный менеджер для учета запросов
    @asynccontextmanager
    async def track_request(self) -> AsyncIterator[None]:
        """
        usage:
        async with tracker.track_request():
            *обработка запроса*
        """
        async with self._lock:
            self._active_requests += 1
            self._idle.clear() # типа мы заняты

        try:
            yield
        finally:
            async with self._lock: # в конце запроса - уменьшаем счетчик
                if self._active_requests > 0:
                    self._active_requests -= 1
                if self._active_requests == 0:
                    self._idle.set() # типа мы не заняты

    # для ready и health
    def snapshot(self) -> dict[str, object]:
        return {
            "draining": self._draining,
            "active_requests": self._active_requests,
            "started_at": self._drain_started_at.isoformat() if self._drain_started_at else None,
            "reason": self._drain_reason,
        }

# для ready и health и middleware
def get_graceful_shutdown_state(app: FastAPI) -> GracefulShutdownState:
    state = getattr(app.state, STATE_KEY, None)
    if state is None:
        state = GracefulShutdownState()
        setattr(app.state, STATE_KEY, state)
    return state


class GracefulShutdownMiddleware:
    """
    Graceful Shutdown Middleware

    При draining:
    - mutating (POST, PUT, DELETE, PATCH) запросы не пускаем
    - отвечаем 503
    - если все ок - пихаем запрос в track request
    """
    def __init__(self, app: ASGIApp, *, retry_after_seconds: int) -> None:
        self.app = app
        self.retry_after_seconds = retry_after_seconds

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        # сам до конца не понял, но так надо
        app = scope.get("app")
        if app is None:
            await self.app(scope, receive, send)
            return

        # инфа о запросе
        method = scope.get("method", "GET").upper()
        path = scope.get("path", "")
        shutdown_state = get_graceful_shutdown_state(app)

        # блокировка mutating запросов, кидаем 503
        if shutdown_state.is_draining and method in MUTATING_METHODS:
            response = JSONResponse(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                content={
                    "detail": "Service is shutting down and is not accepting new write operations.",
                    "status": "draining",
                },
                headers={
                    "Connection": "close",
                    "Retry-After": str(self.retry_after_seconds),
                },
            )
            await response(scope, receive, send)
            return

        # не трекаем всякие /health /ready итп
        if path in UNTRACKED_PATHS:
            await self.app(scope, receive, send)
            return

        # запрос обычный - трекаем как обычно
        async with shutdown_state.track_request():
            await self.app(scope, receive, send)


def install_graceful_shutdown(app: FastAPI, *, retry_after_seconds: int) -> None:
    get_graceful_shutdown_state(app)
    if getattr(app.state, "_graceful_shutdown_middleware_installed", False):
        return
    app.add_middleware(GracefulShutdownMiddleware, retry_after_seconds=retry_after_seconds)
    setattr(app.state, "_graceful_shutdown_middleware_installed", True)
