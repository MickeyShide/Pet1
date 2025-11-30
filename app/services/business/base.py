# infrastructure/business.py
import inspect
from typing import TypeVar, get_type_hints, Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.auth import SAccessToken
from app.services.base import BaseService
from app.utils.err.base.forbidden import ForbiddenException

T = TypeVar("T")


class BaseBusinessService:
    session: AsyncSession | None = None
    token_data: SAccessToken | None = None

    def __init__(self, token_data: SAccessToken | None = None):
        self.token_data = token_data

    def __getattr__(self, name: str) -> Any:  # noqa: D401
        hints = get_type_hints(self.__class__)
        attr_type = hints.get(name)

        if inspect.isclass(attr_type) and issubclass(attr_type, BaseService):
            session = getattr(self, "session", None)
            if session is None:
                raise RuntimeError("No session")
            return attr_type(session)

        raise AttributeError(
            f"'{self.__class__.__name__}' object has no attribute '{name}'"
        )
