import contextlib
import functools
from contextlib import asynccontextmanager

from sqlalchemy.exc import InvalidRequestError
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, AsyncSession, create_async_engine

from app.config import settings

_engine: AsyncEngine | None = None
async_session_maker: async_sessionmaker[AsyncSession] | None = None


def init_engine(echo: bool = False) -> None:
    """
    Initialize the database engine
    :param echo:
    :return:
    """
    global _engine, async_session_maker
    if _engine is not None:
        return
    _engine = create_async_engine(settings.DATABASE_URL, future=True, echo=echo)
    async_session_maker = async_sessionmaker(_engine, expire_on_commit=False)


async def dispose_engine() -> None:
    """
    Dispose the database engine
    :return:
    """
    global _engine
    if _engine is not None:
        await _engine.dispose()
        _engine = None


@asynccontextmanager
async def get_session(*, readonly: bool = False):
    """
    Yield an async session with automatic commit/rollback handling.
    :param readonly:
    :return:
    """
    if async_session_maker is None:
        raise RuntimeError("Engine is not initialized. Call init_engine() first.")

    async with async_session_maker() as session:
        if readonly:
            try:
                yield session
            finally:
                with contextlib.suppress(InvalidRequestError):
                    await session.rollback()
        else:
            await session.begin()
            try:
                yield session
                if session.in_transaction():
                    await session.commit()
            except Exception:
                with contextlib.suppress(InvalidRequestError):
                    if session.in_transaction():
                        await session.rollback()
                raise


def new_session(*, readonly: bool = False):
    """
    Decorator to create a new session with automatic commit/rollback handling.
    :param readonly:
    :return:
    """

    def decorator(func):
        # TODO �?���:�?�? �'�?�' �"���?��'�?�>�?
        @functools.wraps(func)
        async def wrapper(self, *args, **kwargs):
            if async_session_maker is None:
                raise RuntimeError("Engine is not initialized. Call init_engine() first.")

            async with get_session(readonly=readonly) as session:
                setattr(self, "session", session)
                try:
                    # Transaction lifecycle is managed inside get_session
                    result = await func(self, *args, **kwargs)
                    return result
                finally:
                    setattr(self, "session", None)

        return wrapper

    return decorator
