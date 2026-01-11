import asyncio
import os
from unittest.mock import patch

import pytest
import pytest_asyncio.plugin as pytest_asyncio_plugin
from faker import Faker

# Keep pytest-asyncio on a single session loop and fix asyncpg on Windows.
os.environ.setdefault("PYTEST_ASYNCIO_LOOP_SCOPE", "session")
pytest_asyncio_plugin.DEFAULT_LOOP_SCOPE = "session"
if os.name == "nt":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

DEFAULT_AUTOTESTS_PG_URL = "postgresql+asyncpg://app:app@localhost:5438/fastapi_pet_1_autotests"
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://app:app@localhost:5438/fastapi_pet_1_autotests")
os.environ.setdefault("SECRET_KEY", "test-secret")
os.environ.setdefault("ALGORITHM", "HS256")
os.environ.setdefault("ACCESS_TOKEN_EXPIRE_MINUTES", "15")
os.environ.setdefault("REFRESH_TOKEN_EXPIRE_DAYS", "7")
os.environ.setdefault("COOKIE_SECURE", "0")

dotenv_patch = patch("dotenv.main.dotenv_values", return_value={})
dotenv_patch.start()
psettings_patch = patch("pydantic_settings.sources.providers.dotenv.dotenv_values", return_value={})
psettings_patch.start()


@pytest.fixture(scope="session")
def faker():
    return Faker()


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session", autouse=True)
def _stop_dotenv_patch():
    yield
    dotenv_patch.stop()
    psettings_patch.stop()


def pytest_configure(config):
    config.addinivalue_line("markers", "concurrent_db: allow multiple DB sessions in a test")
    config.addinivalue_line("markers", "db_commit: allow real commits in a test")
