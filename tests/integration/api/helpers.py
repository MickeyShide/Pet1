from fastapi import FastAPI

from app.api import deps
from app.schemas.auth import SAccessToken


def override_token(app: FastAPI, token: SAccessToken) -> None:
    app.dependency_overrides[deps.get_token_data] = lambda: token


def override_token_dependency(app: FastAPI, token: SAccessToken) -> None:
    override_token(app, token)


def override_admin_token(app: FastAPI, *, user_id: int | str = "1") -> None:
    override_token(app, SAccessToken(sub=str(user_id), admin=True))


def override_user_token(app: FastAPI, *, user_id: int | str = "1") -> None:
    override_token(app, SAccessToken(sub=str(user_id), admin=False))


def clear_overrides(app: FastAPI) -> None:
    app.dependency_overrides.clear()
