from __future__ import annotations

from urllib.parse import quote

from celery import Celery
from prometheus_client import start_http_server

from app.config import settings
from app.observability.logging import setup_logging

setup_logging(service_name=f"{settings.SERVICE_NAME}-worker")
_METRICS_SERVER_STARTED = False


def start_worker_metrics_server() -> None:
    global _METRICS_SERVER_STARTED
    if _METRICS_SERVER_STARTED:
        return
    start_http_server(addr=settings.CELERY_METRICS_HOST, port=settings.CELERY_METRICS_PORT)
    _METRICS_SERVER_STARTED = True


def build_broker_url() -> str:
    """
    Compose broker URL from explicit env or RabbitMQ settings.
    """
    if settings.CELERY_BROKER_URL:
        return settings.CELERY_BROKER_URL
    user = quote(settings.RABBITMQ_USER)
    password = quote(settings.RABBITMQ_PASSWORD)
    vhost = settings.RABBITMQ_VHOST or "/"
    return f"amqp://{user}:{password}@{settings.RABBITMQ_HOST}:{settings.RABBITMQ_PORT}/{vhost.lstrip('/')}"


def build_result_backend_url() -> str:
    """
    Compose result backend URL. Uses explicit CELERY_RESULT_BACKEND or Redis by default.
    """
    if settings.CELERY_RESULT_BACKEND:
        return settings.CELERY_RESULT_BACKEND
    password = f":{settings.REDIS_PASSWORD}@" if settings.REDIS_PASSWORD else ""
    return f"redis://{password}{settings.REDIS_HOST}:{settings.REDIS_PORT}/{settings.REDIS_DB}"


def create_celery_app() -> Celery:
    celery = Celery(
        "fastapi-pet",
        broker=build_broker_url(),
        backend=build_result_backend_url(),
        include=["app.celery_app.tasks"],
    )
    celery.conf.update(
        task_default_queue="default",
        task_routes={
            "app.celery_app.tasks.*": {"queue": "default"},
            "app.bookings.*": {"queue": "default"},
        },
        worker_prefetch_multiplier=1, # длина очереди у воркера типа, чтобы больше одной не брал
        task_acks_late=True, # подтверждение выполнения ПОСЛЕ выполнения а не когда задачу взял
        task_acks_on_failure_or_timeout=True, # подтверждение при ошибках
        task_reject_on_worker_lost=True, # если воркер умер задача возвращается
    )
    return celery


celery_app = create_celery_app()
start_worker_metrics_server()


@celery_app.task(name="app.celery_app.tasks.ping")
def ping() -> str:
    return "pong"
