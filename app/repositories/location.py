from typing import Any, List

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models.location import Location
from app.repositories.base import BaseRepository


class LocationRepository(BaseRepository[Location]):
    _model_cls = Location

    async def get_all(
            self,
            desc: bool = True,
            offset: int | None = None,
            limit: int | None = None,
            **filters: Any,
    ) -> List[Location]:
        query = (
            select(self._model_cls)
            .options(selectinload(self._model_cls.features))
            .filter_by(**filters)
        )

        if limit is not None:
            query = query.limit(limit)
        if offset is not None:
            query = query.offset(offset)

        if desc:
            query = query.order_by(self._model_cls.id.desc())
        else:
            query = query.order_by(self._model_cls.id)

        res = await self.session.execute(query)
        return list(res.scalars().all())

    async def get_one(self, **filters) -> Location:
        query = (
            select(self._model_cls)
            .options(selectinload(self._model_cls.features))
            .filter_by(**filters)
        )
        res = await self.session.execute(query)
        return res.scalars().one()
