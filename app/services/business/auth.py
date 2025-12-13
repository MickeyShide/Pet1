from jose import JWTError
from starlette.requests import Request
from starlette.responses import Response

from app.config import settings
from app.db.base import new_session
from app.models import User
from app.models.user import UserRole
from app.schemas.auth import SRegister, SLogin, SLoginOut, SAccessToken, SRefreshToken
from app.schemas.user import SUserOut
from app.services.business.base import BaseBusinessService
from app.services.user import UserService
from app.utils.cache import CacheService
from app.utils.cache import keys as cache_keys
from app.utils.err.auth import TooManyAttempts
from app.utils.err.base.not_found import NotFoundException
from app.utils.err.base.unauthorized import UnauthorizedException
from app.utils.security import create_access_token, create_refresh_token, verify_token


class AuthBusinessService(BaseBusinessService):
    user_service: UserService

    _antifraud_ttl_seconds = 6

    @staticmethod
    def _generate_tokens_and_cookie(response: Response, user: User) -> tuple[str, str]:
        """
        Generates a new access token and refresh token.

        Usage: access, refresh = self._generate_tokens(user)
        :param user: User model
        :return: access_token, refresh_token
        """
        access_token = create_access_token(
            SAccessToken(
                sub=str(user.id),
                admin=(user.role == UserRole.ADMIN),
            ).model_dump()
        )

        refresh_token = create_refresh_token(
            SRefreshToken(
                sub=str(user.id)
            ).model_dump()
        )

        response.set_cookie(
            key="refresh_token",
            value=refresh_token,
            httponly=True,
            secure=settings.COOKIE_SECURE,
            samesite="lax",
            max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
            path="/auth/refresh",
        )

        return access_token, refresh_token

    @new_session()
    async def register(self, user_data: SRegister) -> SUserOut:
        result: User = await self.user_service.create_user(user_data)
        return SUserOut.from_model(result)

    @new_session()
    async def login(self, request: Request, response: Response, login_data: SLogin) -> SLoginOut:
        ip_header = request.headers.get("X-Real-IP") or request.headers.get("X-Forwarded-For")
        client_ip = (ip_header.split(",")[0].strip() if ip_header else (request.client.host if request.client else "unknown")) or "unknown"

        cache = CacheService()
        cache_key = cache_keys.login_ip(client_ip)
        cached = await cache.try_get(cache_key)
        if cached is not None:
            await cache.try_set(cache_key, cached + 1, ttl=self._antifraud_ttl_seconds)
            if cached >= 5:
                raise TooManyAttempts()
        else:
            await cache.try_set(cache_key, 1, ttl=self._antifraud_ttl_seconds)

        user: User = await self.user_service.login(login_data)

        access_token, refresh_token = self._generate_tokens_and_cookie(response=response, user=user)

        return SLoginOut(
            access_token=access_token,
            refresh_token=refresh_token,
            user=SUserOut.from_model(user),
        )

    @new_session()
    async def refresh(self, request: Request, response: Response) -> SLoginOut:
        refresh_token = request.cookies.get("refresh_token")
        if not refresh_token:
            raise UnauthorizedException("Missing refresh token")

        try:
            user_data = verify_token(refresh_token)
            user_id = int(user_data["sub"])
            user: User = await self.user_service.get_one_by_id(user_id)
        except (JWTError, NotFoundException):
            raise UnauthorizedException("Invalid refresh token")

        access_token, refresh_token = self._generate_tokens_and_cookie(response=response, user=user)

        return SLoginOut(
            access_token=access_token,
            refresh_token=refresh_token,
            user=SUserOut.from_model(user),
        )

    @new_session()
    async def get_me(self) -> SUserOut:
        user: User = await self.user_service.get_one_by_id(int(self.token_data.sub))
        return SUserOut.from_model(user)
