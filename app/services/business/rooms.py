from app.db.base import new_session
from app.models import Room
from app.schemas.room import SRoomOut, SRoomCreate, SRoomUpdate
from app.services.business.base import BaseBusinessService
from app.services.location import LocationService
from app.services.room import RoomService


class RoomBusinessService(BaseBusinessService):
    location_service: LocationService
    room_service: RoomService

    @new_session()
    async def create_by_location_id(self, location_id: int, room_data: SRoomCreate) -> SRoomOut:
        room: Room = await self.room_service.create(location_id=location_id, **room_data.model_dump())
        return SRoomOut(**room.model_dump())

    @new_session(readonly=True)
    async def get_by_id(self, room_id: int) -> SRoomOut:
        room: Room = await self.room_service.get_one_by_id(room_id)
        return SRoomOut(**room.model_dump())

    @new_session()
    async def update_by_id(self, room_id: int, room_data: SRoomUpdate) -> SRoomOut:
        room: Room = await self.room_service.update_by_id(
            room_id,
            **room_data.model_dump(exclude_unset=True)
        )
        return SRoomOut(**room.model_dump())

    @new_session()
    async def delete_by_id(self, room_id: int) -> None:
        await self.room_service.delete_by_id(room_id)

