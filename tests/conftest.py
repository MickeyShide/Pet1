import asyncio
import os
from unittest.mock import patch

import pytest
import pytest_asyncio
import pytest_asyncio.plugin as pytest_asyncio_plugin
from faker import Faker
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlmodel import SQLModel
from alembic.config import Config as AlembicConfig
from alembic import command as alembic_command

# Keep pytest-asyncio on a single session loop and fix asyncpg on Windows (Proactor incompatibility).
os.environ.setdefault("PYTEST_ASYNCIO_LOOP_SCOPE", "session")
pytest_asyncio_plugin.DEFAULT_LOOP_SCOPE = "session"
if os.name == "nt":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

DEFAULT_AUTOTESTS_PG_URL = "postgresql+asyncpg://app:app@localhost:5438/fastapi_pet_1_autotests"
USE_AUTOTESTS_POSTGRES = os.environ.get("USE_AUTOTESTS_POSTGRES", "0") == "1"
USE_AUTOTESTS_POSTGRES = True
os.environ.setdefault(
    "DATABASE_URL",
    DEFAULT_AUTOTESTS_PG_URL if USE_AUTOTESTS_POSTGRES else "sqlite+aiosqlite:///./test_db.sqlite3",
)
os.environ.setdefault("SECRET_KEY", "test-secret")
os.environ.setdefault("ALGORITHM", "HS256")
os.environ.setdefault("ACCESS_TOKEN_EXPIRE_MINUTES", "15")
os.environ.setdefault("REFRESH_TOKEN_EXPIRE_DAYS", "7")
os.environ.setdefault("COOKIE_SECURE", "0")
DB_URL = os.environ["DATABASE_URL"]
IS_SQLITE = DB_URL.startswith("sqlite")

dotenv_patch = patch("dotenv.main.dotenv_values", return_value={})
dotenv_patch.start()
psettings_patch = patch("pydantic_settings.sources.providers.dotenv.dotenv_values", return_value={})
psettings_patch.start()

from app.db import base as db_base  # noqa: E402
from app.db.base import init_engine  # noqa: E402
from app.models import Booking, Location, Room, TimeSlot, User  # noqa: F401,E402

if IS_SQLITE:
    table_args = getattr(TimeSlot, "__table_args__", ())
    if isinstance(table_args, tuple):
        TimeSlot.__table_args__ = tuple(
            arg
            for arg in table_args
            if getattr(arg, "__visit_name__", None) != "exclude_constraint"
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

@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="function")
async def async_engine():
    # Ensure engine settings are in sync for alembic (settings reads DATABASE_URL)
    os.environ["DATABASE_URL"] = DB_URL
    init_engine()
    engine = create_async_engine(DB_URL, future=True)
    if IS_SQLITE:
        async with engine.begin() as conn:
            await conn.run_sync(SQLModel.metadata.drop_all)
            await conn.run_sync(SQLModel.metadata.create_all)
    else:
        # Apply migrations for Postgres
        config_path = os.path.join(os.path.dirname(__file__), "..", "alembic.ini")
        alembic_cfg = AlembicConfig(file_=config_path)
        alembic_command.upgrade(alembic_cfg, "head")

    yield engine
    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def session_maker(async_engine):
    maker = async_sessionmaker(async_engine, expire_on_commit=False, class_=AsyncSession)
    db_base.async_session_maker = maker
    yield maker
    db_base.async_session_maker = None


@pytest_asyncio.fixture(autouse=True)
async def ensure_session_maker(session_maker):
    yield


@pytest_asyncio.fixture(autouse=True)
async def clean_database(async_engine):
    async with async_engine.begin() as conn:
        for table in reversed(SQLModel.metadata.sorted_tables):
            await conn.execute(table.delete())


@pytest_asyncio.fixture
async def db_session(session_maker):
    async with session_maker() as session:
        yield session


@pytest.fixture(scope="session")
def faker():
    return Faker()


@pytest.fixture(scope="session", autouse=True)
def _stop_dotenv_patch():
    yield
    dotenv_patch.stop()
    psettings_patch.stop()
