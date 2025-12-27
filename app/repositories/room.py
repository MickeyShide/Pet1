from typing import List, Any

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models.room import Room
from app.repositories.base import BaseRepository


class RoomRepository(BaseRepository[Room]):
    _model_cls = Room

    async def get_all_with_location(
            self,
            desc: bool = True,
            offset: int | None = None,
            limit: int | None = None,
            **filters: Any,
    ) -> List[Room]:

        query = (
            select(self._model_cls)
            .options(selectinload(self._model_cls.location))
            .filter_by(**filters)
        )

        if desc:
            query = query.order_by(self._model_cls.id.desc())
        else:
            query = query.order_by(self._model_cls.id)

        if offset is not None:
            query = query.offset(offset)
        if limit is not None:
            query = query.limit(limit)

        res = await self.session.execute(query)
        return list(res.scalars().all())
