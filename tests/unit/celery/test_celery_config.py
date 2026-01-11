import importlib

import pytest


def test_build_broker_url_defaults_amqp(monkeypatch):
    monkeypatch.setenv("CELERY_BROKER_URL", "")
    monkeypatch.setenv("RABBITMQ_USER", "user")
    monkeypatch.setenv("RABBITMQ_PASSWORD", "pass")
    monkeypatch.setenv("RABBITMQ_HOST", "rabbit")
    monkeypatch.setenv("RABBITMQ_PORT", "5679")
    monkeypatch.setenv("RABBITMQ_VHOST", "vhost")

    import app.config as config_module

    importlib.reload(config_module)
    from app.celery_app import app as celery_app_module
    importlib.reload(celery_app_module)
    from app.celery_app.app import build_broker_url

    broker_url = build_broker_url()
    assert broker_url == "amqp://user:pass@rabbit:5679/vhost"


def test_build_result_backend_uses_redis(monkeypatch):
    monkeypatch.setenv("CELERY_RESULT_BACKEND", "")
    monkeypatch.setenv("REDIS_HOST", "redis-host")
    monkeypatch.setenv("REDIS_PORT", "6380")
    monkeypatch.setenv("REDIS_DB", "2")
    monkeypatch.setenv("REDIS_PASSWORD", "pwd")

    import app.config as config_module

    importlib.reload(config_module)
    from app.celery_app import app as celery_app_module
    importlib.reload(celery_app_module)
    from app.celery_app.app import build_result_backend_url

    backend_url = build_result_backend_url()
    assert backend_url == "redis://:pwd@redis-host:6380/2"


@pytest.mark.parametrize("eager", [True])
def test_ping_task_executes_in_eager(monkeypatch, eager):
    monkeypatch.setenv("CELERY_BROKER_URL", "memory://")
    monkeypatch.setenv("CELERY_RESULT_BACKEND", "rpc://")

    import app.config as config_module

    importlib.reload(config_module)
    from app.celery_app import app as celery_app_module
    importlib.reload(celery_app_module)
    from app.celery_app.app import create_celery_app

    celery = create_celery_app()
    celery.conf.task_always_eager = eager
    celery.conf.task_store_eager_result = True

    task = celery.tasks["app.celery_app.tasks.ping"]
    result = task.apply_async()
    assert result.get(timeout=3) == "pong"