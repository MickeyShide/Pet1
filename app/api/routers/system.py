from __future__ import annotations

import anyio
from fastapi import APIRouter
from kombu import Connection
from sqlalchemy import text
from starlette import status
from starlette.responses import JSONResponse

from app.celery_app.app import build_broker_url
from app.db import base as db_base
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


async def _check_rabbitmq() -> tuple[bool, str]:
    try:
        await anyio.to_thread.run_sync(_probe_rabbitmq)
        return True, "ok"
    except Exception as exc:
        return False, str(exc)


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/ready")
async def ready():
    db_ok = await _check_db()
    redis_ok = await _check_redis()
    rabbitmq_ok = await _check_rabbitmq()

    payload: dict[str, object] = {
        "status": "ok" if db_ok and redis_ok and rabbitmq_ok else "degraded",
        "dependencies": {
            "db": db_ok,
            "redis": redis_ok,
            "rabbitmq": rabbitmq_ok,
        },
    }

    if db_ok and redis_ok and rabbitmq_ok:
        return payload
    return JSONResponse(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, content=payload)
