from sqlalchemy.exc import IntegrityError

from app.models import User
from app.models.user import UserRole
from app.repositories.user import UserRepository
from app.schemas.auth import SRegister, SLogin
from app.services.base import BaseService
from app.utils.err.auth import EmailAlreadyTaken, UsernameAlreadyTaken
from app.utils.err.base.not_found import NotFoundException
from app.utils.err.base.unauthorized import UnauthorizedException
from app.utils.security import hash_password, verify_password


class UserService(BaseService[User]):
    _repository = UserRepository

    async def create_user(self, user_data: SRegister) -> User:
        print(user_data)
        hashed = hash_password(user_data.password)

        payload = user_data.model_dump(exclude={"password"})
        payload["hashed_password"] = hashed
        payload["role"] = UserRole.USER

        try:
            return await self.create(**payload)
        except IntegrityError as exc:
            msg = str(exc.orig)

            if "users_email_key" in msg or "email" in msg:
                raise EmailAlreadyTaken()

            if "users_username_key" in msg or "username" in msg:
                raise UsernameAlreadyTaken()

            raise

    async def login(self, login_data: SLogin) -> User:
        try:
            user: User = await self.get_first_by_filters(email=login_data.email)
        except NotFoundException:
            raise UnauthorizedException("Wrong email or password")

        if verify_password(plain_password=login_data.password,
                           hashed_password=user.hashed_password):
            return user
        else:
            raise UnauthorizedException("Wrong email or password")
