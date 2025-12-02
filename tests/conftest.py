import asyncio
import os
from unittest.mock import patch

import pytest
import pytest_asyncio
from faker import Faker
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlmodel import SQLModel

os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///./test_db.sqlite3"
os.environ["SECRET_KEY"] = "test-secret"
os.environ["ALGORITHM"] = "HS256"
os.environ["ACCESS_TOKEN_EXPIRE_MINUTES"] = "15"
os.environ["REFRESH_TOKEN_EXPIRE_DAYS"] = "7"
os.environ["COOKIE_SECURE"] = "0"

dotenv_patch = patch("dotenv.main.dotenv_values", return_value={})
dotenv_patch.start()
psettings_patch = patch("pydantic_settings.sources.providers.dotenv.dotenv_values", return_value={})
psettings_patch.start()

from app.db import base as db_base  # noqa: E402
from app.models import Booking, Location, Room, TimeSlot, User  # noqa: F401,E402

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


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session")
async def async_engine():
    engine = create_async_engine(os.environ["DATABASE_URL"], future=True)
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.drop_all)
        await conn.run_sync(SQLModel.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture(scope="session")
async def session_maker(async_engine):
    maker = async_sessionmaker(async_engine, expire_on_commit=False, class_=AsyncSession)
    db_base.async_session_maker = maker
    yield maker
    db_base.async_session_maker = None


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
