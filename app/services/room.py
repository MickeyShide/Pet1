from app.models import Room
from app.repositories.room import RoomRepository
from app.services.base import BaseService


class RoomService(BaseService[Room]):
    _repository = RoomRepository

    async def get_all_with_location(self) -> list[Room]:
        return await self._repository.get_all_with_location()
