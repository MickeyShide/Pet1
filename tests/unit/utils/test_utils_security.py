import pytest
from jose import JWTError, jwt

from app.config import settings
from app.utils.security import (
    create_access_token,
    create_refresh_token,
    hash_password,
    hash_password_async,
    verify_password,
    verify_password_async,
    verify_token,
)


def test_hash_and_verify_password():
    password = "StrongPass123!"
    hashed = hash_password(password)

    assert hashed != password
    assert verify_password(password, hashed) is True
    assert verify_password("wrong", hashed) is False


@pytest.mark.asyncio
async def test_hash_and_verify_password_async():
    password = "AsyncPass123!"
    hashed = await hash_password_async(password)

    assert hashed != password
    assert await verify_password_async(password, hashed) is True
    assert await verify_password_async("wrong", hashed) is False


def test_create_access_token_contains_payload():
    token = create_access_token({"sub": "1", "admin": True})
    payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])

    assert payload["sub"] == "1"
    assert payload["admin"] is True
    assert "exp" in payload


def test_create_refresh_token_contains_subject():
    token = create_refresh_token({"sub": "9"})
    payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])

    assert payload["sub"] == "9"
    assert "exp" in payload


def test_verify_token_rejects_invalid_signature():
    bad_token = jwt.encode({"sub": "1"}, "wrong", algorithm=settings.ALGORITHM)

    with pytest.raises(JWTError):
        verify_token(bad_token)
