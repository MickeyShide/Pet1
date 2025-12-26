import inspect
from abc import ABC
from typing import TypeVar, Generic, List

from sqlalchemy.exc import NoResultFound
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import BaseSQLModel
from app.repositories.base import BaseRepository
from app.utils.err.base.not_found import NotFoundException

T = TypeVar('T', bound=BaseSQLModel)


class BaseService(Generic[T], ABC):
    _repository: BaseRepository[T]

    def __init__(self, session: AsyncSession):
        self.session = session
        self._init_repository()

    def _init_repository(self) -> None:
        if inspect.isclass(self._repository) and issubclass(self._repository, BaseRepository):
            self._repository = self._repository(self.session)

    async def create(self, **data) -> T:
        """
        Create model via repo and return it.
        :param data: dict with new model data
        :return: Created model
        """
        return await self._repository.create(**data)

    async def update_by_id(self, _id: int, **data) -> T:
        """
        Update model via repo and return it.
        :param _id: model id
        :param data: dict with update data
        :return: Updated model
        """
        try:
            return await self._repository.update_by_id(_id, **data)
        except NoResultFound:
            raise NotFoundException(
                detail=f'no_item_in_{self._repository.model_cls}_with_{_id}_id'
            )

    async def get_first_by_filters(self, **filters) -> T:
        """
        Returns first item by many filters

        :param filters: dict with filter params
        :return: Model
        """

        try:
            return await self._repository.get_first(**filters)
        except NoResultFound:
            raise NotFoundException(
                detail="no_items_found_by_filters"
            )

    async def get_all(self, offset: int | None = None, limit: int | None = None) -> List[T]:
        """
        Returns all objects, can be empty list

        :param offset: query offset
        :param limit: query limit
        :return: list[Model]
        """

        all_elements: List[T] = await self._repository.get_all(offset=offset, limit=limit)

        return [element for element in all_elements]

    async def get_one_by_id(self, _id: int) -> T:
        """
        Returns object by id OR NotFoundException

        :param _id: int
        :return: Object
        """

        try:
            return await self._repository.get_one(id=_id)
        except NoResultFound:
            raise NotFoundException(
                detail=f'no_item_in_{self._repository.model_cls}_with_{_id}_id'
            )

    async def delete_by_id(self, _id: int) -> None:
        """
        Returns nothing, just delete object by id

        :param _id: int
        :return: None
        """

        try:
            result = await self._repository.delete(id=_id)
            return result
        except NoResultFound:
            raise NotFoundException(
                detail=f'no_item_in_{self._repository.model_cls}_with_{_id}_id'
            )

    async def find_all_by_filters(
            self,
            desc: bool = True,
            offset: int | None = None,
            limit: int | None = None,
            **filters
    ) -> list[T]:
        """
        Get all objects filtered by OPTIONAL filters, with limit/offset/desc.

        :param offset: query offset
        :param limit: query limit
        :param desc: desc (True) or asc (False)
        :param filters: any filters
        :return: list[Model]
        """
        return await self._repository.get_all(desc=desc, offset=offset, limit=limit, **filters)
