from __future__ import annotations

from contextvars import ContextVar, Token


# Per-request ctx.
request_id_ctx: ContextVar[str | None] = ContextVar("request_id_ctx", default=None)
user_id_ctx: ContextVar[str | None] = ContextVar("user_id_ctx", default=None)
path_ctx: ContextVar[str | None] = ContextVar("path_ctx", default=None)
method_ctx: ContextVar[str | None] = ContextVar("method_ctx", default=None)


def set_request_id(value: str | None) -> Token:
    return request_id_ctx.set(value)


def reset_request_id(token: Token) -> None:
    request_id_ctx.reset(token)


def get_request_id() -> str | None:
    return request_id_ctx.get()


def set_user_id(value: str | None) -> Token:
    return user_id_ctx.set(value)


def reset_user_id(token: Token) -> None:
    user_id_ctx.reset(token)


def get_user_id() -> str | None:
    return user_id_ctx.get()


def set_path(value: str | None) -> Token:
    return path_ctx.set(value)


def reset_path(token: Token) -> None:
    path_ctx.reset(token)


def get_path() -> str | None:
    return path_ctx.get()


def set_method(value: str | None) -> Token:
    return method_ctx.set(value)


def reset_method(token: Token) -> None:
    method_ctx.reset(token)


def get_method() -> str | None:
    return method_ctx.get()
