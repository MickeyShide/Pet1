from __future__ import annotations

from prometheus_client import CONTENT_TYPE_LATEST, Counter, Gauge, Histogram, generate_latest
from starlette.requests import Request
from starlette.responses import Response

# HTTP metrics.
HTTP_REQUESTS_TOTAL = Counter(
    "http_requests_total",
    "Total number of HTTP requests",
    ["method", "route", "status_code"],
)
HTTP_REQUEST_DURATION_SECONDS = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency in seconds",
    ["method", "route", "status_code"],
    buckets=(
        0.005,
        0.01,
        0.025,
        0.05,
        0.1,
        0.25,
        0.5,
        1.0,
        2.5,
        5.0,
        10.0,
    ),
)
HTTP_REQUESTS_ERRORS_TOTAL = Counter(
    "http_requests_errors_total",
    "HTTP error responses",
    ["method", "route", "status_code", "error_type"],
)
HTTP_REQUESTS_IN_PROGRESS = Gauge(
    "http_requests_in_progress",
    "In-progress HTTP requests",
)

# Business metrics.
BUSINESS_OPERATIONS_IN_PROGRESS = Gauge(
    "business_operations_in_progress",
    "In-progress business operations",
    ["operation"],
)

BOOKING_CREATE_TOTAL = Counter(
    "booking_create_total",
    "Booking create attempts",
    ["result", "source", "operation"],
)
BOOKING_CONFLICTS_TOTAL = Counter(
    "booking_conflicts_total",
    "Booking conflicts",
    ["source", "operation", "reason"],
)
BOOKING_CANCEL_TOTAL = Counter(
    "booking_cancel_total",
    "Booking cancel attempts",
    ["result", "source", "operation"],
)
BOOKING_PAYMENT_CONFIRM_TOTAL = Counter(
    "booking_payment_confirm_total",
    "Booking payment confirmations",
    ["result", "source", "operation"],
)
IDEMPOTENCY_REUSE_TOTAL = Counter(
    "idempotency_reuse_total",
    "Idempotency cache reuses",
    ["source", "operation"],
)
IDEMPOTENCY_CONFLICTS_TOTAL = Counter(
    "idempotency_conflicts_total",
    "Idempotency conflicts",
    ["source", "operation", "reason"],
)


def get_route_label(request: Request) -> str:
    # Prefer route templates.
    route = request.scope.get("route")
    route_path = getattr(route, "path", None)
    if route_path:
        return str(route_path)
    return request.url.path


def observe_http_request(*, method: str, route: str, status_code: int, duration_seconds: float) -> None:
    status = str(status_code)
    method_upper = method.upper()

    HTTP_REQUESTS_TOTAL.labels(method=method_upper, route=route, status_code=status).inc()
    HTTP_REQUEST_DURATION_SECONDS.labels(method=method_upper, route=route, status_code=status).observe(duration_seconds)

    if status_code >= 400:
        # Split client/server.
        error_type = "server" if status_code >= 500 else "client"
        HTTP_REQUESTS_ERRORS_TOTAL.labels(
            method=method_upper,
            route=route,
            status_code=status,
            error_type=error_type,
        ).inc()


def inc_http_requests_in_progress() -> None:
    HTTP_REQUESTS_IN_PROGRESS.inc()


def dec_http_requests_in_progress() -> None:
    HTTP_REQUESTS_IN_PROGRESS.dec()


def inc_business_operation_in_progress(operation: str) -> None:
    BUSINESS_OPERATIONS_IN_PROGRESS.labels(operation=operation).inc()


def dec_business_operation_in_progress(operation: str) -> None:
    BUSINESS_OPERATIONS_IN_PROGRESS.labels(operation=operation).dec()


def observe_booking_create(*, result: str, source: str, operation: str = "create") -> None:
    BOOKING_CREATE_TOTAL.labels(result=result, source=source, operation=operation).inc()


def observe_booking_conflict(*, source: str, operation: str, reason: str) -> None:
    BOOKING_CONFLICTS_TOTAL.labels(source=source, operation=operation, reason=reason).inc()


def observe_booking_cancel(*, result: str, source: str, operation: str = "cancel") -> None:
    BOOKING_CANCEL_TOTAL.labels(result=result, source=source, operation=operation).inc()


def observe_booking_payment_confirm(*, result: str, source: str, operation: str = "confirm_payment") -> None:
    BOOKING_PAYMENT_CONFIRM_TOTAL.labels(result=result, source=source, operation=operation).inc()


def observe_idempotency_reuse(*, source: str, operation: str) -> None:
    IDEMPOTENCY_REUSE_TOTAL.labels(source=source, operation=operation).inc()


def observe_idempotency_conflict(*, source: str, operation: str, reason: str) -> None:
    IDEMPOTENCY_CONFLICTS_TOTAL.labels(source=source, operation=operation, reason=reason).inc()


def metrics_response() -> Response:
    # Prometheus scrape.
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
