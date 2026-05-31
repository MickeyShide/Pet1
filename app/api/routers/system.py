from __future__ import annotations

import anyio
from time import perf_counter
from fastapi import APIRouter, Request
from kombu import Connection
from sqlalchemy import text
from starlette import status
from starlette.responses import JSONResponse

from app.celery_app.app import build_broker_url
from app.db import base as db_base
from app.graceful_shutdown import get_graceful_shutdown_state
from app.observability.metrics import metrics_response, observe_dependency_status, observe_readiness_state
from app.overload import overload_controller
from app.utils.redis import get_redis

router = APIRouter(tags=["System"])


async def _check_db() -> bool:
    started_at = perf_counter()
    if db_base.async_session_maker is None:
        observe_dependency_status(dependency="db", is_up=False, duration_seconds=perf_counter() - started_at)
        return False

    try:
        async with db_base.async_session_maker() as session:
            await session.execute(text("SELECT 1"))
        observe_dependency_status(dependency="db", is_up=True, duration_seconds=perf_counter() - started_at)
        return True
    except Exception:
        observe_dependency_status(dependency="db", is_up=False, duration_seconds=perf_counter() - started_at)
        return False


async def _check_redis() -> bool:
    started_at = perf_counter()
    try:
        redis = await get_redis()
        result = bool(await redis.ping())
        observe_dependency_status(dependency="redis", is_up=result, duration_seconds=perf_counter() - started_at)
        return result
    except Exception:
        observe_dependency_status(dependency="redis", is_up=False, duration_seconds=perf_counter() - started_at)
        return False


def _probe_rabbitmq() -> None:
    with Connection(build_broker_url(), connect_timeout=2) as conn:
        conn.connect()


async def _check_rabbitmq() -> bool:
    started_at = perf_counter()
    try:
        await anyio.to_thread.run_sync(_probe_rabbitmq)
        observe_dependency_status(dependency="rabbitmq", is_up=True, duration_seconds=perf_counter() - started_at)
        return True
    except Exception:
        observe_dependency_status(dependency="rabbitmq", is_up=False, duration_seconds=perf_counter() - started_at)
        return False


@router.get("/health")
async def health(request: Request) -> dict[str, object]:
    return {
        "status": "ok",
        "shutdown": get_graceful_shutdown_state(request.app).snapshot(),
    }


@router.get("/ready")
async def ready(request: Request):
    db_ok = await _check_db()
    redis_ok = await _check_redis()
    rabbitmq_ok = await _check_rabbitmq()
    shutdown_state = get_graceful_shutdown_state(request.app)
    is_draining = shutdown_state.is_draining
    degradation = overload_controller.snapshot()
    is_degraded = degradation["status"] == "degraded"

    payload: dict[str, object] = {
        "status": "draining" if is_draining else "ok" if db_ok and redis_ok and rabbitmq_ok and not is_degraded else "degraded",
        "dependencies": {
            "db": db_ok,
            "redis": redis_ok,
            "rabbitmq": rabbitmq_ok,
        },
        "degradation": degradation,
        "shutdown": shutdown_state.snapshot(),
    }
    observe_readiness_state(
        is_ready=db_ok and redis_ok and rabbitmq_ok and not is_draining and not is_degraded,
        is_draining=is_draining,
    )

    if db_ok and redis_ok and rabbitmq_ok and not is_draining and not is_degraded:
        return payload
    return JSONResponse(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, content=payload)


@router.get("/degradation")
async def degradation() -> dict[str, object]:
    return overload_controller.snapshot()


@router.get("/metrics", include_in_schema=False)
async def metrics():
    return metrics_response()
