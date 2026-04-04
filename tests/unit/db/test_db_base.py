import asyncio

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


@pytest.mark.asyncio
async def test_get_session_rolls_back_on_cancelled_error(monkeypatch):
    class DummySession:
        def __init__(self):
            self.started = False
            self.committed = False
            self.rolled_back = False
            self._in_transaction = False

        async def begin(self):
            self.started = True
            self._in_transaction = True

        async def commit(self):
            self.committed = True
            self._in_transaction = False

        async def rollback(self):
            self.rolled_back = True
            self._in_transaction = False

        def in_transaction(self):
            return self._in_transaction

    class DummySessionContext:
        def __init__(self, session):
            self.session = session

        async def __aenter__(self):
            return self.session

        async def __aexit__(self, exc_type, exc, tb):
            return False

    class DummySessionMaker:
        def __init__(self, session):
            self.session = session

        def __call__(self):
            return DummySessionContext(self.session)

    session = DummySession()
    monkeypatch.setattr(db_base, "async_session_maker", DummySessionMaker(session))

    with pytest.raises(asyncio.CancelledError):
        async with db_base.get_session():
            raise asyncio.CancelledError

    assert session.started is True
    assert session.rolled_back is True
    assert session.committed is False
