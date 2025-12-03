from fastapi import APIRouter
from starlette import status
from starlette.requests import Request
from starlette.responses import Response

from app.api.deps import UserDepends
from app.schemas.auth import STokenOut, SLogin, SRegister
from app.schemas.user import SUserOut
from app.services.business.auth import AuthBusinessService

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post(
    path='/register',
    response_model=SUserOut,
    status_code=status.HTTP_201_CREATED,
    description="Register a new user", )
async def register_route(user_data: SRegister) -> SUserOut:
    return await AuthBusinessService().register(user_data)


@router.post(
    path='/login',
    response_model=STokenOut,
    status_code=status.HTTP_200_OK,
    description="Login a user", )
async def login_route(request: Request, response: Response, login_data: SLogin) -> STokenOut:
    return await AuthBusinessService().login(request, response, login_data)


@router.post(
    path='/refresh',
    response_model=STokenOut,
    status_code=status.HTTP_200_OK,
    description="Refresh tokens by refresh_token", )
async def refresh_route(request: Request, response: Response) -> STokenOut:
    return await AuthBusinessService().refresh(request, response)


@router.get("/me")
async def get_me(token_data: UserDepends) -> SUserOut:
    return await AuthBusinessService(token_data).get_me()
