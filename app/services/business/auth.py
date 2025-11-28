from jose import JWTError
from starlette.requests import Request
from starlette.responses import Response

from app.config import settings
from app.db.base import new_session
from app.models import User
from app.models.user import UserRole
from app.schemas.business.auth import SRegister, SLogin, STokenOut, SAccessToken, SRefreshToken
from app.schemas.user import SUserOut
from app.services.business.base import BaseBusinessService
from app.services.user import UserService
from app.utils.err.base.not_found import NotFoundException
from app.utils.err.base.unauthorized import UnauthorizedException
from app.utils.security import create_access_token, create_refresh_token, verify_token


class AuthBusinessService(BaseBusinessService):
    user_service: UserService

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
            # TODO sdelat'
            # path=self._refresh_cookie_path(),
        )

        return access_token, refresh_token

    @new_session()
    async def register(self, user_data: SRegister) -> SUserOut:
        result: User = await self.user_service.create_user(user_data)
        return SUserOut(**result.model_dump())

    @new_session()
    async def login(self, response: Response, login_data: SLogin) -> STokenOut:
        user: User = await self.user_service.login(login_data)

        access_token, refresh_token = self._generate_tokens_and_cookie(response=response, user=user)

        return STokenOut(
            access_token=access_token
        )

    @new_session()
    async def refresh(self, request: Request, response: Response) -> STokenOut:
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

        return STokenOut(
            access_token=access_token
        )

    @new_session()
    async def get_me(self) -> SUserOut:
        user: User = await self.user_service.get_one_by_id(int(self.token_data.sub))
        return SUserOut(**user.model_dump())