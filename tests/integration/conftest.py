from __future__ import annotations

import os
from contextlib import asynccontextmanager
from contextvars import ContextVar
from typing import AsyncIterator

import pytest
import pytest_asyncio
from alembic import command as alembic_command
from alembic.config import Config as AlembicConfig
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlmodel import SQLModel

from app.db import base as db_base
from app.db.base import init_engine
from app.models import Booking, Location, Room, TimeSlot, User
from app.models.user import UserRole
from tests.factories import UserFactory

DB_URL = os.environ["DATABASE_URL"]
IS_SQLITE = DB_URL.startswith("sqlite")

_CURRENT_SESSION: ContextVar[AsyncSession | None] = ContextVar("CURRENT_TEST_SESSION", default=None)


def _strip_sqlite_constraints() -> None:
    table_args = getattr(TimeSlot, "__table_args__", ())
    if isinstance(table_args, tuple):
        TimeSlot.__table_args__ = tuple(
            arg for arg in table_args if getattr(arg, "__visit_name__", None) != "exclude_constraint"
        )
    timeslot_table = getattr(TimeSlot, "__table__", None)
    if timeslot_table is not None:
        for constraint in list(timeslot_table.constraints):
            if getattr(constraint, "__visit_name__", None) == "exclude_constraint":
                timeslot_table.constraints.discard(constraint)

    bookings_table = getattr(Booking, "__table__", None)
    if bookings_table is not None:
        for index in list(bookings_table.indexes):
            if index.name == "uq_bookings_timeslot_active":
                bookings_table.indexes.discard(index)


@pytest_asyncio.fixture(scope="session")
async def async_engine():
    os.environ["DATABASE_URL"] = DB_URL
    init_engine()
    engine = create_async_engine(DB_URL, future=True)
    if IS_SQLITE:
        _strip_sqlite_constraints()
        async with engine.begin() as conn:
            await conn.run_sync(SQLModel.metadata.drop_all)
            await conn.run_sync(SQLModel.metadata.create_all)
    else:
        config_path = os.path.join(os.path.dirname(__file__), "..", "..", "alembic.autotests.ini")
        alembic_cfg = AlembicConfig(file_=config_path)
        alembic_command.upgrade(alembic_cfg, "head")

    yield engine
    await engine.dispose()


@asynccontextmanager
async def _get_test_session(*, readonly: bool = False) -> AsyncIterator[AsyncSession]:
    session = _CURRENT_SESSION.get()
    if session is None:
        raise RuntimeError("Test session is not initialized. Use db_session fixture.")
    nested = None
    if not readonly:
        nested = await session.begin_nested()
    try:
        yield session
        if not readonly:
            await session.flush()
            if nested is not None and nested.is_active:
                await nested.commit()
    except Exception:
        if nested is not None and nested.is_active:
            await nested.rollback()
        raise


async def _truncate_database(engine) -> None:
    async with engine.begin() as conn:
        for table in reversed(SQLModel.metadata.sorted_tables):
            await conn.execute(table.delete())


@pytest_asyncio.fixture(scope="function")
async def db_session(request, async_engine, monkeypatch):
    maker = async_sessionmaker(async_engine, expire_on_commit=False, class_=AsyncSession)
    db_base.async_session_maker = maker

    use_real_commits = bool(
        request.node.get_closest_marker("concurrent_db")
        or request.node.get_closest_marker("db_commit")
    )

    if use_real_commits:
        async with maker() as session:
            yield session
        await _truncate_database(async_engine)
        db_base.async_session_maker = None
        return

    async with maker() as session:
        token = _CURRENT_SESSION.set(session)
        monkeypatch.setattr(db_base, "get_session", _get_test_session)
        await session.begin()
        try:
            yield session
        finally:
            await session.rollback()
            _CURRENT_SESSION.reset(token)
            db_base.async_session_maker = None


@pytest_asyncio.fixture(autouse=True)
async def ensure_session_maker(request, async_engine):
    if "db_session" in request.fixturenames:
        yield
        return
    was_none = db_base.async_session_maker is None
    if was_none:
        db_base.async_session_maker = async_sessionmaker(
            async_engine,
            expire_on_commit=False,
            class_=AsyncSession,
        )
    try:
        yield
    finally:
        if was_none:
            db_base.async_session_maker = None


class _SharedSessionMaker:
    def __init__(self, session: AsyncSession):
        self._session = session

    def __call__(self):
        @asynccontextmanager
        async def _ctx():
            original_commit = self._session.commit
            original_rollback = self._session.rollback
            nested = await self._session.begin_nested()

            async def _commit():
                await self._session.flush()
                if nested.is_active:
                    await nested.commit()

            async def _rollback():
                if nested.is_active:
                    await nested.rollback()

            self._session.commit = _commit
            self._session.rollback = _rollback
            try:
                yield self._session
            finally:
                self._session.commit = original_commit
                self._session.rollback = original_rollback

        return _ctx()


@pytest_asyncio.fixture
async def session_maker(db_session, async_engine, request):
    if request.node.get_closest_marker("concurrent_db") or request.node.get_closest_marker("db_commit"):
        return async_sessionmaker(async_engine, expire_on_commit=False, class_=AsyncSession)
    return _SharedSessionMaker(db_session)


@pytest_asyncio.fixture
async def user(db_session, faker):
    return await UserFactory.create(db_session, faker, role=UserRole.USER)


@pytest_asyncio.fixture
async def admin_user(db_session, faker):
    return await UserFactory.create(db_session, faker, role=UserRole.ADMIN)


@pytest.fixture(autouse=True)
def _mock_celery_apply_async(monkeypatch):
    """
    Avoid real broker connections during tests; make expire_booking scheduling a no-op.
    """
    try:
        import app.celery_app.manager as celery_manager
    except Exception:
        celery_manager = None

    try:
        import app.services.business.bookings as bookings_module
    except Exception:
        return

    if celery_manager is not None:
        async def _fake_expire_booking(*args, **kwargs):
            return {}

        monkeypatch.setattr(celery_manager.CeleryManager, "expire_booking", _fake_expire_booking)

    if hasattr(bookings_module, "expire_booking"):
        monkeypatch.setattr(bookings_module.expire_booking, "apply_async", lambda *args, **kwargs: None)
