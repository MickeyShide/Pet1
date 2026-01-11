import asyncio

import pytest
from fakeredis.aioredis import FakeRedis

from app.utils.cache.cache_service import CacheService


@pytest.mark.asyncio
async def test_cache_service_set_get_delete():
    redis = FakeRedis(decode_responses=True)
    cache = CacheService(redis_client=redis, prefix="test:cache:")

    payload = {"foo": "bar", "num": 1}
    await cache.set("key", payload)

    cached = await cache.get("key")
    assert cached == payload

    await cache.delete("key")
    assert await cache.get("key") is None


@pytest.mark.asyncio
async def test_cache_service_ttl_expires():
    redis = FakeRedis(decode_responses=True)
    cache = CacheService(redis_client=redis, prefix="test:cache:")

    await cache.set("ttl-key", {"value": 1}, ttl=1)
    await asyncio.sleep(1.1)

    assert await cache.get("ttl-key") is None
