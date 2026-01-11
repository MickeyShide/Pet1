from starlette.requests import Request
from starlette.responses import Response

from app.db.base import new_session
from app.models import User
from app.schemas.auth import SRegister, SLogin, SLoginOut
from app.schemas.user import SUserOut
from app.services.business.base import BaseBusinessService
from app.services.user import UserService


class AuthBusinessService(BaseBusinessService):
    user_service: UserService

    @new_session()
    async def register(self, user_data: SRegister) -> SUserOut:
        result: User = await self.user_service.create_user(user_data)

        return SUserOut.from_model(result)

    @new_session()
    async def login(self, request: Request, response: Response, login_data: SLogin) -> SLoginOut:
        await self.user_service.antifraud(request=request)
        user: User = await self.user_service.login(login_data)
        access_token, refresh_token = await self.user_service.generate_tokens_and_cookie(response=response, user=user)

        return SLoginOut(
            access_token=access_token,
            user=SUserOut.from_model(user),
        )

    @new_session()
    async def logout(self, response: Response):
        await self.user_service.delete_cookies(response=response)

    @new_session()
    async def refresh(self, request: Request, response: Response) -> SLoginOut:
        user: User = await self.user_service.get_user_from_refresh_token(request=request)
        access_token, refresh_token = await self.user_service.generate_tokens_and_cookie(response=response, user=user)

        return SLoginOut(
            access_token=access_token,
            user=SUserOut.from_model(user),
        )

    @new_session()
    async def get_me(self) -> SUserOut:
        user: User = await self.user_service.get_one_by_id(self.user_id)

        return SUserOut.from_model(user)
