from __future__ import annotations

from prometheus_client import CONTENT_TYPE_LATEST, Counter, Gauge, Histogram, generate_latest
from starlette.requests import Request
from starlette.responses import Response

DEFAULT_LATENCY_BUCKETS = (
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
)

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
    buckets=DEFAULT_LATENCY_BUCKETS,
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
APP_UP = Gauge(
    "app_up",
    "Application process is up",
)
APP_READINESS_STATUS = Gauge(
    "app_readiness_status",
    "Application readiness status",
)
APP_DRAINING_STATUS = Gauge(
    "app_draining_status",
    "Application draining mode status",
)
DEPENDENCY_STATUS = Gauge(
    "dependency_status",
    "Dependency availability status",
    ["dependency"],
)
DEPENDENCY_CHECK_DURATION_SECONDS = Histogram(
    "dependency_check_duration_seconds",
    "Dependency readiness check duration in seconds",
    ["dependency", "result"],
    buckets=DEFAULT_LATENCY_BUCKETS,
)

# Business metrics.
BUSINESS_OPERATIONS_IN_PROGRESS = Gauge(
    "business_operations_in_progress",
    "In-progress business operations",
    ["operation"],
)
BUSINESS_OPERATION_DURATION_SECONDS = Histogram(
    "business_operation_duration_seconds",
    "Business operation latency in seconds",
    ["operation", "result"],
    buckets=DEFAULT_LATENCY_BUCKETS,
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
PAYMENT_GATEWAY_OPERATIONS_TOTAL = Counter(
    "payment_gateway_operations_total",
    "Payment gateway operations",
    ["operation", "result"],
)
PAYMENT_GATEWAY_OPERATION_DURATION_SECONDS = Histogram(
    "payment_gateway_operation_duration_seconds",
    "Payment gateway latency in seconds",
    ["operation", "result"],
    buckets=DEFAULT_LATENCY_BUCKETS,
)
PAYMENT_GATEWAY_RETRIES_TOTAL = Counter(
    "payment_gateway_retries_total",
    "Payment gateway retry attempts",
    ["operation", "error_type"],
)
PAYMENT_GATEWAY_ERRORS_TOTAL = Counter(
    "payment_gateway_errors_total",
    "Payment gateway errors",
    ["operation", "error_type"],
)
BACKGROUND_TASKS_TOTAL = Counter(
    "background_tasks_total",
    "Background task executions",
    ["task", "result"],
)
BACKGROUND_TASK_DURATION_SECONDS = Histogram(
    "background_task_duration_seconds",
    "Background task duration in seconds",
    ["task", "result"],
    buckets=DEFAULT_LATENCY_BUCKETS,
)
BACKGROUND_TASK_SCHEDULE_LAG_SECONDS = Histogram(
    "background_task_schedule_lag_seconds",
    "Background task lag between scheduled time and actual execution",
    ["task", "result"],
    buckets=DEFAULT_LATENCY_BUCKETS,
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


def observe_business_operation_duration(*, operation: str, result: str, duration_seconds: float) -> None:
    BUSINESS_OPERATION_DURATION_SECONDS.labels(operation=operation, result=result).observe(duration_seconds)


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


def observe_dependency_status(*, dependency: str, is_up: bool, duration_seconds: float) -> None:
    result = "up" if is_up else "down"
    DEPENDENCY_STATUS.labels(dependency=dependency).set(1 if is_up else 0)
    DEPENDENCY_CHECK_DURATION_SECONDS.labels(dependency=dependency, result=result).observe(duration_seconds)


def observe_readiness_state(*, is_ready: bool, is_draining: bool) -> None:
    APP_READINESS_STATUS.set(1 if is_ready else 0)
    APP_DRAINING_STATUS.set(1 if is_draining else 0)


def observe_payment_gateway_operation(*, operation: str, result: str, duration_seconds: float) -> None:
    PAYMENT_GATEWAY_OPERATIONS_TOTAL.labels(operation=operation, result=result).inc()
    PAYMENT_GATEWAY_OPERATION_DURATION_SECONDS.labels(operation=operation, result=result).observe(duration_seconds)


def observe_payment_gateway_retry(*, operation: str, error_type: str) -> None:
    PAYMENT_GATEWAY_RETRIES_TOTAL.labels(operation=operation, error_type=error_type).inc()


def observe_payment_gateway_error(*, operation: str, error_type: str) -> None:
    PAYMENT_GATEWAY_ERRORS_TOTAL.labels(operation=operation, error_type=error_type).inc()


def observe_background_task(*, task: str, result: str, duration_seconds: float, lag_seconds: float | None = None) -> None:
    BACKGROUND_TASKS_TOTAL.labels(task=task, result=result).inc()
    BACKGROUND_TASK_DURATION_SECONDS.labels(task=task, result=result).observe(duration_seconds)
    if lag_seconds is not None:
        BACKGROUND_TASK_SCHEDULE_LAG_SECONDS.labels(task=task, result=result).observe(max(0.0, lag_seconds))


def metrics_response() -> Response:
    # Prometheus scrape.
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


APP_UP.set(1)
