# Pet1 Booking Service

FastAPI booking service with SQLAlchemy/SQLModel, PostgreSQL, Redis, RabbitMQ/Celery, MinIO, and Prometheus/Grafana observability.

## Labs 6-8

### Lab 6: monitoring

Implemented observability for API, business services, background tasks, and dependencies:

- Structured JSON logs with `request_id`, method, path, status code, latency, timestamp, service name, and error context.
- HTTP request middleware that logs request start/finish/failure and records latency/error metrics.
- Business event logging for booking creation, booking conflicts, booking cancellation, payment confirmation, payment gateway retries, and background task execution.
- Prometheus metrics at `GET /metrics`.
- Readiness dependency probes for PostgreSQL, Redis, and RabbitMQ.
- Degradation state at `GET /degradation` and inside `GET /ready`.
- Grafana/Prometheus assets under `docker/observability`.

Important metrics:

- `http_requests_total`
- `http_request_duration_seconds`
- `http_requests_errors_total`
- `http_requests_in_progress`
- `business_operations_in_progress`
- `business_operation_duration_seconds`
- `booking_create_total`
- `booking_conflicts_total`
- `booking_cancel_total`
- `booking_payment_confirm_total`
- `payment_gateway_operations_total`
- `payment_gateway_operation_duration_seconds`
- `payment_gateway_retries_total`
- `payment_gateway_errors_total`
- `background_tasks_total`
- `background_task_duration_seconds`
- `background_task_schedule_lag_seconds`
- `dependency_status`
- `dependency_check_duration_seconds`
- `app_readiness_status`
- `app_draining_status`

### Lab 7: overload response

Implemented configurable overload protection for heavy operations:

- Booking creation and flexible booking creation.
- Payment creation and confirmation.
- MinIO image upload presign operations.
- Background task scheduling through Celery/RabbitMQ.

Limits are configured in `app.config.Settings` with `OVERLOAD_*` settings:

- Max active operations.
- Sliding-window rate limits.
- Queue pressure threshold.
- Operation timeout.
- `Retry-After` value for rejected requests.

Overload/degradation responses use stable `detail` payloads:

```json
{
  "detail": {
    "error_code": "rate_limit_exceeded",
    "message": "Rate limit exceeded for booking_create",
    "retry_after": 5
  }
}
```

Dependency degradation returns `503` and includes `degraded_component`; rate and active-operation limits return `429`; operation timeouts return `504`.

### Lab 8: final scenarios

Added lightweight scenario tests for:

- Concurrent booking requests for the same slot.
- Read-only endpoint load.
- Payment gateway failure/degradation.
- Graceful shutdown behavior is covered by the existing API and DB shutdown tests.
- Existing booking race/idempotency tests cover database consistency after concurrent requests.

## Running Locally

Install dependencies:

```bash
python -m pip install -r requirements.txt
```

Start autotest PostgreSQL:

```bash
docker compose -f docker/compose.autotests.yml up -d
```

Run the full test suite:

```bash
pytest
```

Run focused slices:

```bash
pytest tests/unit/test_overload.py tests/unit/api/test_degradation_endpoint.py tests/unit/test_failure_scenarios.py
pytest tests/integration/api/test_lab8_load_scenarios.py
pytest -m load
pytest -m failure
```

Start the local stack:

```bash
docker compose -f docker/compose.yml up --build
```

Useful endpoints:

- `GET /health`
- `GET /ready`
- `GET /metrics`
- `GET /degradation`
