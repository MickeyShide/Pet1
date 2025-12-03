from fastapi import FastAPI
from redis.asyncio import Redis

from app.config import settings

_redis_client: Redis | None = None


def _build_client() -> Redis:
    return Redis(
        host=settings.REDIS_HOST,
        port=settings.REDIS_PORT,
        db=settings.REDIS_DB,
        password=settings.REDIS_PASSWORD or None,
        decode_responses=True,
        encoding="utf-8",
        health_check_interval=30,
        socket_connect_timeout=1.0,
    )


async def get_redis() -> Redis:
    """
    Return Redis client
    """
    global _redis_client
    if _redis_client is None:
        _redis_client = _build_client()
    return _redis_client


async def init_redis(app: FastAPI | None = None) -> None:
    """
    Initialize Redis on startup
    """
    global _redis_client
    if _redis_client is None:
        _redis_client = _build_client()

    try:
        await _redis_client.ping()
    except Exception:
        _redis_client = None
    else:
        if app is not None:
            app.state.redis = _redis_client


async def close_redis(app: FastAPI | None = None) -> None:
    """
    Close Redis on shutdown.
    """
    global _redis_client
    client = _redis_client
    _redis_client = None

    if client is None:
        return

    try:
        await client.aclose()
    except Exception:
        pass
    finally:
        if app is not None:
            app.state.redis = None


__all__ = ["get_redis", "init_redis", "close_redis"]
