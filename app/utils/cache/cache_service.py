import json
from typing import Generic, TypeVar, Type

from redis.asyncio import Redis

from app.config import settings
from app.schemas import BaseSchema
from app.utils.redis import get_redis

T = TypeVar("T")


class CacheService(Generic[T]):
    """
    Универсальный кеш поверх Redis.

    Режимы использования:

    1) Без явной модели (сырой JSON, dict, list, примитивы):
        cache = CacheService()
        await cache.set("key", {"a": 1})
        data = await cache.get("key")   # -> dict | list | примитив (как положили)

        # для удаления типа вообще не нужно
        await CacheService().delete("key")

    2) Типобезопасный режим с Pydantic/BaseSchema (одна модель):
        user_cache: CacheService[SUserOut] = CacheService(model=SUserOut)
        await user_cache.set("user:1", user_obj, ttl=60)
        cached_user = await user_cache.get("user:1")  # -> SUserOut | None

    3) Типобезопасный режим с Pydantic/BaseSchema (список моделей):
        from typing import List

        timeslot_cache: CacheService[List[STimeSlotOutWithBookingStatus]] = CacheService(
            model=STimeSlotOutWithBookingStatus,
            collection=True,
        )
        await timeslot_cache.set("timeslots:key", timeslots_list, ttl=60)
        cached_timeslots = await timeslot_cache.get("timeslots:key")
        # -> list[STimeSlotOutWithBookingStatus] | None
    """

    def __init__(
            self,
            *,
            model: Type[BaseSchema] | None = None,
            collection: bool = False,
            redis_client: Redis | None = None,
            prefix: str | None = None,
    ) -> None:
        # model = None → «сырой JSON» режим (dict/list/primitive)
        if model is not None and not issubclass(model, BaseSchema):
            raise TypeError("model must be subclass of BaseSchema")

        self.model: Type[BaseSchema] | None = model
        # если model=None, флаг collection ни на что не влияет
        self._collection_mode = collection if model is not None else False

        self._redis_client = redis_client
        self._prefix = prefix if prefix is not None else settings.REDIS_CACHE_PREFIX

    async def _client(self) -> Redis | None:
        """
        Safe lazy Redis client init
        """
        if self._redis_client is not None:
            return self._redis_client

        try:
            self._redis_client = await get_redis()
            return self._redis_client
        except Exception:
            return None

    def _full_key(self, key: str) -> str:
        return f"{self._prefix}{key}"

    # ----------------- сериализация / десериализация -----------------

    def _serialize(self, value: T) -> str:
        """
        BaseSchema / list[BaseSchema] / dict / list / primitive -> JSON
        """
        # Режим без модели: просто json.dumps(value)
        if self.model is None:
            return json.dumps(value, default=str)

        # Режим с BaseSchema
        if self._collection_mode:
            # ожидаем list[BaseSchema]
            if not isinstance(value, list):
                raise TypeError("Expected list[...] for collection cache.")
            payload = [item.model_dump() for item in value]  # type: ignore[attr-defined]
        else:
            # одиночная модель
            payload = value.model_dump()  # type: ignore[attr-defined]

        return json.dumps(payload, default=str)

    def _deserialize(self, raw: str) -> T | None:
        """
        JSON -> BaseSchema / list[BaseSchema] / dict / list / primitive
        """
        try:
            data = json.loads(raw)
        except Exception:
            return None

        # Режим без модели: возвращаем как есть (dict/list/primitive)
        if self.model is None:
            return data  # type: ignore[return-value]

        # Режим с BaseSchema
        try:
            if self._collection_mode:
                if not isinstance(data, list):
                    return None
                result_list = []
                for item in data:
                    obj = self.model.model_validate(item)  # type: ignore[attr-defined]
                    result_list.append(obj)
                return result_list  # type: ignore[return-value]
            else:
                obj = self.model.model_validate(data)  # type: ignore[attr-defined]
                return obj  # type: ignore[return-value]
        except Exception:
            return None

    # ------------------------- публичные методы -----------------------

    async def get(self, key: str) -> T | None:
        """
        Get object by key OR None
        """
        client = await self._client()
        if client is None:
            return None

        full_key = self._full_key(key)
        try:
            raw_value = await client.get(full_key)
        except Exception:
            return None

        if raw_value is None:
            return None

        if isinstance(raw_value, bytes):
            try:
                raw_value = raw_value.decode("utf-8")
            except Exception:
                return None

        return self._deserialize(raw_value)

    async def set(self, key: str, value: T, ttl: int | None = None) -> None:
        """
        Set object by key + TTL in sec
        """
        client = await self._client()
        if client is None:
            return

        full_key = self._full_key(key)
        try:
            serialized = self._serialize(value)
            if ttl is not None:
                await client.setex(full_key, ttl, serialized)
            else:
                await client.set(full_key, serialized)
        except Exception:
            return

    async def delete(self, key: str) -> None:
        """
        Delete object by key

        Можно вызывать даже на CacheService() без model.
        """
        client = await self._client()
        if client is None:
            return

        full_key = self._full_key(key)
        try:
            await client.delete(full_key)
        except Exception:
            return

    async def delete_pattern(self, pattern: str) -> None:
        """
        Delete all objects matching the pattern

        Example: await cache.delete_pattern("timeslots:*")
        """
        client = await self._client()
        if client is None:
            return

        try:
            async for prefixed_key in client.scan_iter(
                    match=self._full_key(pattern)
            ):
                await client.delete(prefixed_key)
        except Exception:
            return

    async def try_get(self, key: str, default: T | None = None) -> T | None:
        """
        Safe get object by key OR default
        """
        value = await self.get(key)
        return default if value is None else value

    async def try_set(self, key: str, value: T, ttl: int | None = None) -> None:
        """
        Safe set (ignore Redis errors)
        """
        await self.set(key, value, ttl=ttl)

    async def try_delete(self, key: str) -> None:
        """
        Safe delete (ignore Redis errors)
        """
        await self.delete(key)
