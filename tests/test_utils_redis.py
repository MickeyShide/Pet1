import pytest
from fastapi import FastAPI

from app.utils import redis as redis_utils


class _GoodClient:
    def __init__(self):
        self.closed = False

    async def ping(self):
        return True

    async def aclose(self):
        self.closed = True


class _BadPingClient(_GoodClient):
    async def ping(self):
        raise RuntimeError("ping failed")


class _BadCloseClient(_GoodClient):
    async def aclose(self):
        self.closed = True
        raise RuntimeError("close failed")


@pytest.mark.asyncio
async def test_init_redis_sets_state(monkeypatch):
    client = _GoodClient()
    monkeypatch.setattr(redis_utils, "_redis_client", None, raising=False)
    monkeypatch.setattr(redis_utils, "_build_client", lambda: client)

    app = FastAPI()
    await redis_utils.init_redis(app)

    assert app.state.redis is client
    assert redis_utils._redis_client is client

    await redis_utils.close_redis(app)
    assert app.state.redis is None


@pytest.mark.asyncio
async def test_init_redis_failure_resets_client(monkeypatch):
    client = _BadPingClient()
    monkeypatch.setattr(redis_utils, "_redis_client", None, raising=False)
    monkeypatch.setattr(redis_utils, "_build_client", lambda: client)

    app = FastAPI()
    await redis_utils.init_redis(app)

    assert redis_utils._redis_client is None
    await redis_utils.close_redis(app)


@pytest.mark.asyncio
async def test_close_redis_handles_close_errors(monkeypatch):
    client = _BadCloseClient()
    monkeypatch.setattr(redis_utils, "_redis_client", client, raising=False)

    app = FastAPI()
    await redis_utils.close_redis(app)

    assert app.state.redis is None
