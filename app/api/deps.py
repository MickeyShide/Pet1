# app/api/deps.py
from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import jwt, JWTError

from app.config import settings
from app.schemas.auth import SAccessToken
from app.utils.err.base.forbidden import ForbiddenException
from app.utils.err.base.unauthorized import UnauthorizedException

_http_bearer = HTTPBearer(auto_error=False)
HTTPBearerDepends = Annotated[HTTPAuthorizationCredentials | None, Depends(_http_bearer)]


async def get_token_data(jwt_token: HTTPBearerDepends) -> SAccessToken:
    if jwt_token is None:
        raise UnauthorizedException("Missing access token")
    try:
        payload = jwt.decode(
            jwt_token.credentials,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
        )
    except JWTError:
        raise UnauthorizedException("Invalid access token")

    try:
        return SAccessToken(**payload)
    except (TypeError, ValueError) as e:
        print(e)
        raise UnauthorizedException("Invalid access token subject")


async def get_admin_token_data(token: SAccessToken = Depends(get_token_data)) -> SAccessToken:
    if token.admin:
        return token
    else:
        raise ForbiddenException("Not allowed")


UserDepends = Annotated[SAccessToken, Depends(get_token_data)]

AdminDepends = Annotated[SAccessToken, Depends(get_admin_token_data)]
