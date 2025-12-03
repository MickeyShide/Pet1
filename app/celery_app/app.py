from __future__ import annotations

from urllib.parse import quote

from celery import Celery

from app.config import settings


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
    celery.conf.task_default_queue = "default"
    celery.conf.task_routes = {"app.celery_app.tasks.*": {"queue": "default"}}
    return celery


celery_app = create_celery_app()


@celery_app.task(name="app.celery_app.tasks.ping")
def ping() -> str:
    return "pong"
