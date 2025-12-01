from app.db.base import new_session
from app.schemas.timeslot import STimeSlotUpdate
from app.services.business.base import BaseBusinessService
from app.services.location import LocationService
from app.services.room import RoomService
from app.services.timeslot import TimeSlotService


class TimeSlotBusinessService(BaseBusinessService):
    location_service: LocationService
    room_service: RoomService
    timeslots_service: TimeSlotService

    @new_session()
    async def update_timeslot_by_id(self, timeslot_id: int, timeslot_data: STimeSlotUpdate):
        return await self.timeslots_service.update_by_id(
            timeslot_id, **timeslot_data.model_dump(exclude_unset=True)
        )

    @new_session()
    async def delete_timeslot_by_id(self, timeslot_id: int):
        await self.timeslots_service.delete_by_id(timeslot_id)
