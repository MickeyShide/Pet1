from __future__ import annotations

import logging
from time import perf_counter
from uuid import uuid4

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.observability.context import (
    reset_method,
    reset_path,
    reset_request_id,
    reset_user_id,
    set_method,
    set_path,
    set_request_id,
    set_user_id,
)
from app.observability.metrics import (
    dec_http_requests_in_progress,
    get_route_label,
    inc_http_requests_in_progress,
    observe_http_request,
)

logger = logging.getLogger("app.observability.http")


class RequestObservabilityMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("X-Request-ID") or str(uuid4())
        request.state.request_id = request_id

        # Bind request ctx.
        token_request_id = set_request_id(request_id)
        token_user_id = set_user_id(None)
        token_path = set_path(request.url.path)
        token_method = set_method(request.method.upper())

        # Default error state.
        started_at = perf_counter()
        status_code = 500
        response: Response | None = None

        # Count live requests.
        inc_http_requests_in_progress()

        logger.info(
            "http_request_started",
            extra={
                "event": "http_request_started",
                "path": request.url.path,
                "method": request.method.upper(),
            },
        )

        try:
            response = await call_next(request)
            status_code = response.status_code
            response.headers["X-Request-ID"] = request_id
            return response
        except Exception as exc:
            logger.exception(
                "http_request_failed",
                extra={
                    "event": "http_request_failed",
                    "path": request.url.path,
                    "method": request.method.upper(),
                    "status_code": status_code,
                    "error_code": "unhandled_exception",
                    "exception_type": type(exc).__name__,
                },
            )
            raise
        finally:
            duration_seconds = perf_counter() - started_at
            duration_ms = round(duration_seconds * 1000, 3)
            route = get_route_label(request)

            # Record request stats.
            observe_http_request(
                method=request.method.upper(),
                route=route,
                status_code=status_code,
                duration_seconds=duration_seconds,
            )
            dec_http_requests_in_progress()

            logger.info(
                "http_request_finished",
                extra={
                    "event": "http_request_finished",
                    "path": route,
                    "method": request.method.upper(),
                    "status_code": status_code,
                    "duration_ms": duration_ms,
                },
            )

            # Clear request ctx.
            reset_request_id(token_request_id)
            reset_user_id(token_user_id)
            reset_path(token_path)
            reset_method(token_method)
