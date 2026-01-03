from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP

from app.models import Room
from app.repositories.room import RoomRepository
from app.services.base import BaseService


class RoomService(BaseService[Room]):
    _repository = RoomRepository

    async def get_all_with_location(self) -> list[Room]:
        return await self._repository.get_all_with_location()

    async def get_price_quote(
            self,
            room_id: int,
            date_from: datetime,
            date_to: datetime,
    ) -> Decimal:
        hour_price: Decimal = await self._repository.get_hour_price(room_id)

        duration_seconds = Decimal(
            (date_to - date_from).total_seconds()
        )
        hours = duration_seconds / 3600

        total_price = hour_price * hours

        return total_price.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
