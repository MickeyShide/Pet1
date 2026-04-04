from __future__ import annotations

import anyio
from fastapi import APIRouter, Request
from kombu import Connection
from sqlalchemy import text
from starlette import status
from starlette.responses import JSONResponse

from app.celery_app.app import build_broker_url
from app.db import base as db_base
from app.graceful_shutdown import get_graceful_shutdown_state
from app.utils.redis import get_redis

router = APIRouter(tags=["System"])


async def _check_db() -> bool:
    if db_base.async_session_maker is None:
        return False

    try:
        async with db_base.async_session_maker() as session:
            await session.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


async def _check_redis() -> bool:
    try:
        redis = await get_redis()
        return bool(await redis.ping())
    except Exception:
        return False


def _probe_rabbitmq() -> None:
    with Connection(build_broker_url(), connect_timeout=2) as conn:
        conn.connect()


async def _check_rabbitmq() -> bool:
    try:
        await anyio.to_thread.run_sync(_probe_rabbitmq)
        return True
    except Exception as exc:
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

    payload: dict[str, object] = {
        "status": "draining" if is_draining else "ok" if db_ok and redis_ok and rabbitmq_ok else "degraded",
        "dependencies": {
            "db": db_ok,
            "redis": redis_ok,
            "rabbitmq": rabbitmq_ok,
        },
        "shutdown": shutdown_state.snapshot(),
    }

    if db_ok and redis_ok and rabbitmq_ok and not is_draining:
        return payload
    return JSONResponse(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, content=payload)
