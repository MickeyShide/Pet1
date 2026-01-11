import anyio
from jose import JWTError
from sqlalchemy.exc import IntegrityError
from starlette.requests import Request
from starlette.responses import Response

from app.config import settings
from app.models import User
from app.models.user import UserRole
from app.repositories.user import UserRepository
from app.schemas.auth import SRegister, SLogin, SAccessToken, SRefreshToken
from app.services.base import BaseService
from app.utils.cache import CacheService
from app.utils.cache import keys as cache_keys
from app.utils.err.auth import EmailAlreadyTaken, UsernameAlreadyTaken
from app.utils.err.auth import TooManyAttempts
from app.utils.err.base.not_found import NotFoundException
from app.utils.err.base.unauthorized import UnauthorizedException
from app.utils.security import hash_password, verify_password, create_access_token, create_refresh_token, verify_token


class UserService(BaseService[User]):
    _repository = UserRepository

    _antifraud_ttl_seconds = 6

    async def antifraud(self, request: Request) -> None:
        ip_header = request.headers.get("X-Real-IP") or request.headers.get("X-Forwarded-For")
        client_ip = (ip_header.split(",")[0].strip() if ip_header else (
            request.client.host if request.client else "unknown")) or "unknown"

        cache = CacheService()
        cache_key = cache_keys.login_ip(client_ip)
        cached = await cache.try_get(cache_key)
        if cached is not None:
            await cache.try_set(cache_key, cached + 1, ttl=self._antifraud_ttl_seconds)
            if cached >= 5:
                raise TooManyAttempts()
        else:
            await cache.try_set(cache_key, 1, ttl=self._antifraud_ttl_seconds)

    async def get_user_from_refresh_token(self, request: Request) -> User:

        refresh_token = request.cookies.get("refresh_token")
        if not refresh_token:
            raise UnauthorizedException("Missing refresh token")

        try:
            user_data = verify_token(refresh_token)
            user_id = int(user_data["sub"])
            return await self.get_one_by_id(user_id)
        except (JWTError, NotFoundException):
            raise UnauthorizedException("Invalid refresh token")


    @staticmethod
    async def delete_cookies(response: Response):
        """
        Just delete cookies :3
        """
        response.delete_cookie(
            key="refresh_token",
            httponly=True,
            secure=settings.COOKIE_SECURE,
            samesite="none",
            # path="/auth/refresh",
        )

    @staticmethod
    async def generate_tokens_and_cookie(response: Response, user: User) -> tuple[str, str]:
        """
        Generates a new access token and refresh token.
        """
        access_token = create_access_token(
            SAccessToken(
                sub=str(user.id),
                admin=(user.role == UserRole.ADMIN),
            ).to_dict()
        )

        refresh_token = create_refresh_token(
            SRefreshToken(
                sub=str(user.id)
            ).to_dict()
        )

        response.set_cookie(
            key="refresh_token",
            value=refresh_token,
            httponly=True,
            secure=settings.COOKIE_SECURE,
            samesite="none",
            max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
            # path="/auth/refresh",
        )

        return access_token, refresh_token

    async def create_user(self, user_data: SRegister) -> User:
        hashed = await anyio.to_thread.run_sync(hash_password, user_data.password)

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

        ok = await anyio.to_thread.run_sync(
            verify_password,
            login_data.password,
            user.hashed_password,
        )
        if ok:
            return user
        raise UnauthorizedException("Wrong email or password")
