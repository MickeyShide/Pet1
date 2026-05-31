# Pet1 Monitoring

## Import

1. If Grafana is started from this repo, the dashboard is provisioned automatically from `docker/observability/grafana/dashboards/pet1-observability.json`.
2. For manual import: Grafana -> Dashboards -> New -> Import -> upload `docker/observability/grafana/dashboards/pet1-observability.json`.
3. Prometheus datasource UID must stay `prometheus`, Loki datasource UID must stay `loki`.
4. After changing metrics config, restart `backend`, `worker`, and `prometheus`.

## What to watch

- `HTTP Latency P50/P99`: sustained `p99 > 1s` means API slowdown; `p99 > 2.5s` is critical.
- `HTTP Error Rate`: sustained `> 2%` is bad; `> 5%` is critical.
- `Top HTTP Routes by P99`: use it to find the exact route causing latency spikes.
- `Business Operations P50/P99`: sustained `booking_*` or `confirm_payment` `p99 > 1.5s` means DB, Redis, broker, or gateway pressure.
- `Payment Gateway Retries and Errors`: any stable non-zero retry/error rate deserves attention; `retry_exhausted` or `rejected` spikes are incident signals.
- `Dependencies State`: any `0` for `db`, `redis`, or `rabbitmq` means readiness degradation.
- `Background Task Schedule Lag P50/P99`: `p99 > 5s` is warning, `p99 > 10s` is critical for booking expiration flow.
- `Background Task Runtime and Outcomes`: look for `error`/`cancelled` lines or growing task duration.
- `Anomaly Logs`: contains structured warnings for `slow_http_request`, `slow_business_operation`, `payment_gateway_retry`, `payment_gateway_slow`, and `background_task_schedule_lag`.

## Notes

- Worker metrics are scraped from `pet1-worker` on port `9101`.
- In the current compose setup the worker runs with `--pool=solo` so task metrics are exported consistently.
