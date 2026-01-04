import pytest
from sqlalchemy.exc import IntegrityError

from app.schemas.auth import SLogin, SRegister
from app.services.user import UserService
from app.utils.err.auth import UsernameAlreadyTaken, EmailAlreadyTaken
from app.utils.err.base.unauthorized import UnauthorizedException


@pytest.mark.asyncio
async def test_user_service_login_unknown_email_raises(db_session):
    service = UserService(db_session)

    with pytest.raises(UnauthorizedException):
        await service.login(SLogin(email="missing@example.com", password="pass"))


@pytest.mark.asyncio
async def test_user_service_login_wrong_password_raises(db_session, faker):
    service = UserService(db_session)
    user = await service.create_user(
        SRegister(
            first_name=faker.first_name(),
            second_name=faker.last_name(),
            email=faker.unique.email(),
            username=faker.unique.user_name(),
            password="CorrectPass123!",
        )
    )

    with pytest.raises(UnauthorizedException):
        await service.login(SLogin(email=user.email, password="wrong"))


@pytest.mark.asyncio
async def test_create_user_conflict_prioritizes_username(monkeypatch, db_session):
    service = UserService(db_session)

    async def fail_create(**kwargs):
        raise IntegrityError("stmt", "params", Exception("users_username_key"))

    monkeypatch.setattr(service, "create", fail_create)

    with pytest.raises(UsernameAlreadyTaken):
        await service.create_user(
            SRegister(
                first_name="a",
                second_name="b",
                email="x@y.z",
                username="user",
                password="pass",
            )
        )


@pytest.mark.asyncio
async def test_create_user_conflict_email_raises(monkeypatch, db_session):
    service = UserService(db_session)

    async def fail_create(**kwargs):
        raise IntegrityError("stmt", "params", Exception("users_email_key"))

    monkeypatch.setattr(service, "create", fail_create)

    with pytest.raises(EmailAlreadyTaken):
        await service.create_user(
            SRegister(
                first_name="a",
                second_name="b",
                email="x@y.z",
                username="user",
                password="pass",
            )
        )
