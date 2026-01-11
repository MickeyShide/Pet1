import pytest
from fastapi.security import HTTPAuthorizationCredentials
from jose import jwt

from app.api import deps
from app.config import settings
from app.schemas.auth import SAccessToken
from app.utils.err.base.forbidden import ForbiddenException
from app.utils.err.base.unauthorized import UnauthorizedException


@pytest.mark.asyncio
async def test_get_token_data_invalid_payload_raises_unauthorized():
    bad_token = jwt.encode({"sub": "1"}, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=bad_token)

    with pytest.raises(UnauthorizedException):
        await deps.get_token_data(credentials)


@pytest.mark.asyncio
async def test_get_admin_token_data_forbidden_when_not_admin():
    token = SAccessToken(sub="123", admin=False)

    with pytest.raises(ForbiddenException):
        await deps.get_admin_token_data(token)


@pytest.mark.asyncio
async def test_get_admin_token_data_passes_for_admin():
    token = SAccessToken(sub="42", admin=True)
    result = await deps.get_admin_token_data(token)
    assert result is token
