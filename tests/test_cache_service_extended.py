import pytest
from fakeredis.aioredis import FakeRedis

from app.schemas import BaseSchema
from app.utils.cache.cache_service import CacheService


class DummySchema(BaseSchema):
    name: str


@pytest.mark.asyncio
async def test_cache_service_rejects_invalid_model_type():
    with pytest.raises(TypeError):
        CacheService(model=int)  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_cache_service_model_roundtrip(monkeypatch):
    redis = FakeRedis(decode_responses=True)
    cache = CacheService[DummySchema](model=DummySchema, redis_client=redis, prefix="cache:")

    payload = DummySchema(name="demo")
    await cache.set("model", payload)

    restored = await cache.get("model")
    assert isinstance(restored, DummySchema)
    assert restored.name == "demo"


@pytest.mark.asyncio
async def test_cache_service_collection_requires_list():
    cache = CacheService[DummySchema](model=DummySchema, collection=True, redis_client=FakeRedis(decode_responses=True))

    with pytest.raises(TypeError):
        cache._serialize(DummySchema(name="fail"))  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_cache_service_deserialize_guards(monkeypatch):
    cache = CacheService[DummySchema](model=DummySchema, collection=True, redis_client=FakeRedis(decode_responses=True))

    assert cache._deserialize("not-json") is None
    # Not a list -> should return None
    assert cache._deserialize('{"name": "demo"}') is None
    # Invalid schema payload -> None because validation fails
    assert cache._deserialize('[{"unexpected": "field"}]') is None


@pytest.mark.asyncio
async def test_cache_service_returns_default_when_client_missing(monkeypatch):
    async def raise_client():
        raise RuntimeError("boom")

    monkeypatch.setattr("app.utils.cache.cache_service.get_redis", raise_client)
    cache = CacheService(prefix="no-client:")

    assert await cache.try_get("missing", default={"fallback": True}) == {"fallback": True}
    assert await cache.delete("missing") is None
    assert await cache.set("missing", {"a": 1}) is None
    assert await cache.delete_pattern("pattern:*") is None


@pytest.mark.asyncio
async def test_cache_service_handles_bytes_decode_error(monkeypatch):
    class BadClient:
        def __init__(self):
            self.deleted = []

        async def get(self, key):
            return b"\xff\xfe"

    cache = CacheService(redis_client=BadClient(), prefix="decode:")
    assert await cache.get("any") is None


@pytest.mark.asyncio
async def test_cache_service_delete_and_try_delete_swallow_errors(monkeypatch):
    class ErrorClient:
        def __init__(self):
            self.deleted = []

        async def delete(self, key):
            self.deleted.append(key)
            raise RuntimeError("fail")

    client = ErrorClient()
    cache = CacheService(redis_client=client, prefix="err:")

    assert await cache.delete("k1") is None
    await cache.try_delete("k2")
    assert client.deleted == ["err:k1", "err:k2"]


@pytest.mark.asyncio
async def test_cache_service_delete_pattern_handles_exceptions(monkeypatch):
    class ScanErrorClient:
        def scan_iter(self, match):
            async def _gen():
                raise RuntimeError("scan fail")
                yield None  # pragma: no cover

            return _gen()

    cache = CacheService(redis_client=ScanErrorClient(), prefix="scan:")
    assert await cache.delete_pattern("anything:*") is None
