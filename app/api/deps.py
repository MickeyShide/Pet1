# app/api/deps.py
from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import jwt, JWTError

from app.config import settings
from app.schemas.auth import SAccessToken
from app.utils.err.base.unauthorized import UnauthorizedException

HTTPBearerDepends = Annotated[HTTPAuthorizationCredentials, Depends(HTTPBearer())]


async def get_user_id_from_token(jwt_token: HTTPBearerDepends) -> SAccessToken:
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
    except (TypeError, ValueError):
        raise UnauthorizedException("Invalid access token subject")


UserDepends = Annotated[SAccessToken, Depends(get_user_id_from_token)]
