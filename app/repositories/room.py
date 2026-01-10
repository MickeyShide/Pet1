from decimal import Decimal
from typing import List, Any

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models.location import Location
from app.models.room import Room
from app.repositories.base import BaseRepository
from app.schemas.room import SRoomFilter


class RoomRepository(BaseRepository[Room]):
    _model_cls = Room

    async def get_all(
            self,
            desc: bool = True,
            offset: int | None = None,
            limit: int | None = None,
            **filters: Any,
    ) -> List[Room]:
        query = (
            select(self._model_cls)
            .options(selectinload(self._model_cls.features))
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

    async def get_one(self, **filters) -> Room:
        query = (
            select(self._model_cls)
            .options(selectinload(self._model_cls.features))
            .filter_by(**filters)
        )
        res = await self.session.execute(query)
        return res.scalars().one()

    async def get_all_with_location(
            self,
            filters: SRoomFilter,
            page: int | None = None,
            limit: int | None = None,
    ) -> List[Room]:

        query = (
            select(self._model_cls)
            .options(
                selectinload(self._model_cls.features),
                selectinload(self._model_cls.images),
                selectinload(self._model_cls.location).selectinload(Location.images),
                selectinload(self._model_cls.location).selectinload(Location.features),
            )
            .filter_by(**filters.to_dict())
        )

        if page is not None:
            query = query.offset(page*limit)
        if limit is not None:
            query = query.limit(limit)

        res = await self.session.execute(query)
        return list(res.scalars().all())

    async def get_hour_price(self, room_id: int) -> Decimal:
        query = (
            select(self._model_cls.hour_price)
        ).where(
            self._model_cls.id == room_id
        )
        res = await self.session.execute(query)
        return res.scalar()
