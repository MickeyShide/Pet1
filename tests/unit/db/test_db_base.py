import pytest

from app.db import base as db_base


@pytest.mark.asyncio
async def test_get_session_requires_initialized_engine(monkeypatch):
    monkeypatch.setattr(db_base, "async_session_maker", None)

    with pytest.raises(RuntimeError):
        async with db_base.get_session():
            pass


@pytest.mark.asyncio
async def test_dispose_engine_resets_engine(monkeypatch):
    class DummyEngine:
        def __init__(self):
            self.disposed = False

        async def dispose(self):
            self.disposed = True

    dummy = DummyEngine()
    monkeypatch.setattr(db_base, "_engine", dummy)

    await db_base.dispose_engine()

    assert dummy.disposed is True
    assert getattr(db_base, "_engine") is None


@pytest.mark.asyncio
async def test_new_session_without_engine_raises(monkeypatch):
    class DummyService:
        @db_base.new_session()
        async def do(self):
            return "ok"

    monkeypatch.setattr(db_base, "async_session_maker", None)
    service = DummyService()

    with pytest.raises(RuntimeError):
        await service.do()
