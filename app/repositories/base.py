from abc import ABC
from typing import TypeVar, Generic, Type, List

from sqlalchemy import insert, select, update, delete, Result
from sqlalchemy.exc import NoResultFound
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.base import BaseSQLModel

T = TypeVar("T", bound=BaseSQLModel)


# TODO нахуя тут ABC
class BaseRepository(Generic[T], ABC):
    _model_cls: Type[BaseSQLModel] = None

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, **data) -> T:
        """
        Create a new object and return it.
        :param data:
        :return:
        """
        query = insert(self._model_cls).values(**data).returning(self._model_cls)
        res = await self.session.execute(query)
        return res.scalar_one()

    async def get_all(self,
                      desc: bool = True,
                      offset: int | None = None,
                      limit: int | None = None,
                      **filters) -> List[T]:
        """
        Get all objects filtered by OPTIONAL filters, with limit/offset/desc.
        :param offset: query offset
        :param limit: query limit

        :param desc: desc (True) or asc (False)
        :param filters: any filters
        :return: list[Model]
        """
        query = select(self._model_cls).filter_by(**filters)

        if limit:
            query = query.limit(limit)
        if offset:
            query = query.offset(offset)

        if desc:
            query = query.order_by(self._model_cls.id.desc())
        else:
            query = query.order_by(self._model_cls.id)

        res = await self.session.execute(query)
        return [_ for _ in res.scalars().all()]

    async def get_one(self, **filters) -> T:
        """
        Get one object filtered by OPTIONAL filters.
        :param filters:
        :return:
        """
        query = select(self._model_cls).filter_by(**filters)
        res = await self.session.execute(query)
        return res.scalars().one()

    async def delete(self, **filters) -> None:
        """
        Delete one object filtered by OPTIONAL filters.
        :param filters:
        :return:
        """
        query = delete(self._model_cls).filter_by(**filters)
        result: Result = await self.session.execute(query)
        if result.rowcount == 0:
            raise NoResultFound

    async def update_by_id(self, _id: int, **data) -> T:
        """
        Update one object by id.
        :param _id:
        :param data:
        :return:
        """
        query = (
            update(self._model_cls)
            .where(self._model_cls.id == _id)
            .values(**data)
            .execution_options(synchronize_session=False)
            .returning(self._model_cls)
        )
        result = await self.session.execute(query)
        updated = result.scalar_one_or_none()
        if updated is None:
            raise NoResultFound
        await self.session.refresh(updated)
        return updated

    async def get_first(self, **filters) -> T:
        """
        Get first object filtered by OPTIONAL filters.
        :param filters:
        :return:
        """
        query = select(self._model_cls).filter_by(**filters)
        res = await self.session.execute(query)
        res = res.scalars().first()
        if not res:
            raise NoResultFound
        return res

    @property
    def model_cls(self) -> str:
        return self._model_cls.__tablename__
