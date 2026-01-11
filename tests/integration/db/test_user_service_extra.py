import pytest
from sqlalchemy.exc import IntegrityError

from app.schemas.auth import SRegister
from app.services.user import UserService


@pytest.mark.asyncio
async def test_user_service_reraises_unknown_integrity_error(monkeypatch, db_session, faker):
    service = UserService(db_session)

    async def fail_create(**kwargs):
        raise IntegrityError("stmt", "params", Exception("other"))

    monkeypatch.setattr(service, "create", fail_create)

    with pytest.raises(IntegrityError):
        await service.create_user(
            SRegister(
                first_name=faker.first_name(),
                second_name=faker.last_name(),
                email=faker.unique.email(),
                username=faker.unique.user_name(),
                password="pass",
            )
        )
