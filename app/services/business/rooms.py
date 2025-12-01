from typing import List, Tuple

from app.db.base import new_session
from app.models import Room, TimeSlot
from app.schemas.room import SRoomOut, SRoomCreate, SRoomUpdate
from app.schemas.timeslot import STimeSlotDateRange, STimeSlotOutWithBookingStatus, STimeSlotCreate, STimeSlotOut
from app.services.business.base import BaseBusinessService
from app.services.location import LocationService
from app.services.room import RoomService
from app.services.timeslot import TimeSlotService


class RoomBusinessService(BaseBusinessService):
    location_service: LocationService
    room_service: RoomService
    timeslots_service: TimeSlotService

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

    @new_session(readonly=True)
    async def get_timeslots_by_date_range_with_booking_flag(
            self,
            room_id: int,
            date_range: STimeSlotDateRange
    ) -> List[STimeSlotOutWithBookingStatus]:
        timeslots_with_booking: List[Tuple[TimeSlot, bool]] = (
            await self.timeslots_service.get_all_by_room_id_and_date_range(
                room_id=room_id, date_from=date_range.date_from, date_to=date_range.date_to
            )
        )

        return [
            STimeSlotOutWithBookingStatus(
                **STimeSlotOut.from_model(slot).model_dump(),
                has_active_booking=has_active_booking
            )
            for slot, has_active_booking in timeslots_with_booking
        ]

    @new_session()
    async def create_timeslot(self, room_id: int, timeslot_data: STimeSlotCreate) -> STimeSlotOut:
        new_slot = await self.timeslots_service.create(room_id=room_id, **timeslot_data.model_dump())
        return STimeSlotOut.from_model(new_slot)
