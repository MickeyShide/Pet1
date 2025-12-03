from app.db.base import new_session
from app.schemas.timeslot import STimeSlotUpdate
from app.services.business.base import BaseBusinessService
from app.utils.cache.cache_service import CacheService
from app.utils.cache import keys as cache_keys
from app.services.location import LocationService
from app.services.room import RoomService
from app.services.timeslot import TimeSlotService


class TimeSlotBusinessService(BaseBusinessService):
    location_service: LocationService
    room_service: RoomService
    timeslots_service: TimeSlotService

    @new_session()
    async def update_timeslot_by_id(self, timeslot_id: int, timeslot_data: STimeSlotUpdate):
        updated = await self.timeslots_service.update_by_id(
            timeslot_id, **timeslot_data.model_dump(exclude_unset=True)
        )
        await CacheService().delete_pattern(cache_keys.timeslots_room_prefix(updated.room_id))
        return updated

    @new_session()
    async def delete_timeslot_by_id(self, timeslot_id: int):
        timeslot = await self.timeslots_service.get_one_by_id(timeslot_id)
        await self.timeslots_service.delete_by_id(timeslot_id)
        await CacheService().delete_pattern(cache_keys.timeslots_room_prefix(timeslot.room_id))
