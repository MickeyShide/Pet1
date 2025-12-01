# infrastructure/business.py
import inspect
from typing import TypeVar, get_type_hints, Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.auth import SAccessToken
from app.services.base import BaseService

T = TypeVar("T")


class BaseBusinessService:
    session: AsyncSession | None = None
    token_data: SAccessToken | None = None
    user_id: int | None = None
    admin: bool | None = None

    def __init__(self, token_data: SAccessToken | None = None):
        self.token_data = token_data
        if self.token_data is not None:
            self.user_id = int(self.token_data.sub)
            self.admin = self.token_data.admin

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
