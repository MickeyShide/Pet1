from datetime import datetime

from app.db.base import new_session
from app.schemas.timeslot import STimeSlotUpdate, STimeSlotRangeOut
from app.services.business.base import BaseBusinessService
from app.services.location import LocationService
from app.services.room import RoomService
from app.services.timeslot import TimeSlotService
from app.utils.cache import keys as cache_keys
from app.utils.cache.cache_service import CacheService


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

    @new_session(readonly=True)
    async def get_by_room_and_date_range(
        self,
        room_id: int,
        date_from: datetime,
        date_to: datetime,
    ) -> list[STimeSlotRangeOut]:
        timeslots_with_booking = await self.timeslots_service.get_all_by_room_id_and_date_range(
            room_id=room_id,
            date_from=date_from,
            date_to=date_to,
        )
        result: list[STimeSlotRangeOut] = []
        for slot, _has_active_booking in timeslots_with_booking:
            label = f"{slot.start_datetime:%H:%M} - {slot.end_datetime:%H:%M}"
            hours = (slot.end_datetime - slot.start_datetime).total_seconds() / 3600
            result.append(
                STimeSlotRangeOut(
                    id=str(slot.id),
                    date_from=slot.start_datetime,
                    date_to=slot.end_datetime,
                    label=label,
                    hours=hours,
                )
            )
        return result
