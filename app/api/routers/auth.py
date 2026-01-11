from fastapi import APIRouter
from starlette import status
from starlette.requests import Request
from starlette.responses import Response

from app.api import docs
from app.api.deps import UserDepends
from app.schemas.auth import SLoginOut, SLogin, SRegister
from app.schemas.user import SUserOut
from app.services.business.auth import AuthBusinessService

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post(
    path='/register',
    response_model=SUserOut,
    status_code=status.HTTP_201_CREATED,
    description="Register a new user",
    responses={
        status.HTTP_201_CREATED: docs.response_with_example(
            "User created",
            docs.USER_EXAMPLE,
            model=SUserOut,
        ),
        status.HTTP_409_CONFLICT: docs.error_response(
            "Conflict",
            {
                "email_taken": docs.example(
                    "Email already taken",
                    {"detail": "User with this email already exists"},
                ),
                "username_taken": docs.example(
                    "Username already taken",
                    {"detail": "Username already taken"},
                ),
            },
        ),
        status.HTTP_422_UNPROCESSABLE_ENTITY: docs.error_response(
            "Validation Error",
            {
                "invalid_payload": docs.example(
                    "Validation error",
                    docs.VALIDATION_ERROR_EXAMPLE,
                )
            },
        ),
    },
)
async def register_route(user_data: SRegister) -> SUserOut:
    return await AuthBusinessService().register(user_data)


@router.post(
    path='/login',
    response_model=SLoginOut,
    status_code=status.HTTP_200_OK,
    description="Login a user",
    responses={
        status.HTTP_200_OK: docs.response_with_example(
            "Login successful",
            docs.LOGIN_OUT_EXAMPLE,
            model=SLoginOut,
        ),
        status.HTTP_401_UNAUTHORIZED: docs.error_response(
            "Unauthorized",
            {
                "wrong_credentials": docs.example(
                    "Wrong email or password",
                    {"detail": "Wrong email or password"},
                )
            },
        ),
        status.HTTP_429_TOO_MANY_REQUESTS: docs.error_response(
            "Too Many Requests",
            {
                "too_many_attempts": docs.example(
                    "Too many auth attempts",
                    {"detail": "Too many auth attempts"},
                )
            },
        ),
        status.HTTP_422_UNPROCESSABLE_ENTITY: docs.error_response(
            "Validation Error",
            {
                "invalid_payload": docs.example(
                    "Validation error",
                    docs.VALIDATION_ERROR_EXAMPLE,
                )
            },
        ),
    },
)
async def login_route(request: Request, response: Response, login_data: SLogin) -> SLoginOut:
    return await AuthBusinessService().login(request, response, login_data)


@router.post(
    path='/logout',
    status_code=status.HTTP_200_OK,
    description="Logout a user",
    responses={
        status.HTTP_200_OK: docs.response_with_example(
            "Logged out",
            None,
        )
    },
)
async def logout_route(response: Response):
    return await AuthBusinessService().logout(response)


@router.post(
    path='/refresh',
    response_model=SLoginOut,
    status_code=status.HTTP_200_OK,
    description="Refresh tokens by refresh_token",
    responses={
        status.HTTP_200_OK: docs.response_with_example(
            "Tokens refreshed",
            docs.LOGIN_OUT_EXAMPLE,
            model=SLoginOut,
        ),
        status.HTTP_401_UNAUTHORIZED: docs.error_response(
            "Unauthorized",
            {
                "missing_refresh_token": docs.example(
                    "Missing refresh token",
                    {"detail": "Missing refresh token"},
                ),
                "invalid_refresh_token": docs.example(
                    "Invalid refresh token",
                    {"detail": "Invalid refresh token"},
                ),
            },
        ),
    },
)
async def refresh_route(request: Request, response: Response) -> SLoginOut:
    return await AuthBusinessService().refresh(request, response)


@router.get(
    "/me",
    response_model=SUserOut,
    status_code=status.HTTP_200_OK,
    description="Get current user",
    responses={
        status.HTTP_200_OK: docs.response_with_example(
            "Current user",
            docs.USER_EXAMPLE,
            model=SUserOut,
        ),
        status.HTTP_401_UNAUTHORIZED: docs.error_response(
            "Unauthorized",
            {
                "missing_access_token": docs.example(
                    "Missing access token",
                    {"detail": "Missing access token"},
                ),
                "invalid_access_token": docs.example(
                    "Invalid access token",
                    {"detail": "Invalid access token"},
                ),
            },
        ),
    },
)
async def get_me(token_data: UserDepends) -> SUserOut:
    return await AuthBusinessService(token_data).get_me()
