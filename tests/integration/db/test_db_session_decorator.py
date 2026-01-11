import pytest
from sqlalchemy import select

from app.db import base as db_base
from app.models import Location

pytestmark = pytest.mark.db_commit


class DummyService:
    @db_base.new_session()
    async def create_location(self, name: str) -> None:
        self.session.add(
            Location(
                name=name,
                address="Test street",
                description="Test desc",
            )
        )

    @db_base.new_session()
    async def create_then_fail(self, name: str) -> None:
        self.session.add(
            Location(
                name=name,
                address="Fail street",
                description="Fail desc",
            )
        )
        raise RuntimeError("boom")

    @db_base.new_session(readonly=True)
    async def create_readonly(self, name: str) -> None:
        self.session.add(
            Location(
                name=name,
                address="Read street",
                description="Read desc",
            )
        )
        await self.session.flush()


@pytest.mark.asyncio
async def test_new_session_commits_changes(db_session):
    service = DummyService()

    await service.create_location("Committed")

    result = (await db_session.execute(select(Location).where(Location.name == "Committed"))).scalar_one_or_none()
    assert result is not None


@pytest.mark.asyncio
async def test_new_session_rolls_back_on_exception(db_session):
    service = DummyService()

    with pytest.raises(RuntimeError):
        await service.create_then_fail("RolledBack")

    result = (await db_session.execute(select(Location).where(Location.name == "RolledBack"))).scalar_one_or_none()
    assert result is None


@pytest.mark.asyncio
async def test_new_session_readonly_rolls_back(db_session):
    service = DummyService()

    await service.create_readonly("ReadOnly")

    result = (await db_session.execute(select(Location).where(Location.name == "ReadOnly"))).scalar_one_or_none()
    assert result is None
