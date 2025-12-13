import pytest

from app.repositories.location import LocationRepository


@pytest.mark.asyncio
async def test_base_repository_get_all_supports_limit_offset_and_order(db_session, faker):
    repo = LocationRepository(db_session)
    created = []
    for suffix in ["a", "b", "c"]:
        created.append(
            await repo.create(
                name=f"loc-{suffix}",
                address=faker.address(),
                description="desc",
            )
        )

    results = await repo.get_all(desc=False, limit=2, offset=1)

    assert len(results) == 2
    assert [loc.id for loc in results] == [created[1].id, created[2].id]


def test_notificationlog_repository_module_imports():
    from app.repositories.notificationlog import NotificationLogRepository

    assert NotificationLogRepository._model_cls.__tablename__ == "notificationlogs"
