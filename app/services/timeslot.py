from datetime import datetime

from sqlalchemy.exc import NoResultFound

from app.models import TimeSlot
from app.repositories.timeslot import TimeSlotRepository
from app.services.base import BaseService
from app.utils.err.booking import TimeSlotNotFound, SlotAlreadyTaken


class TimeSlotService(BaseService[TimeSlot]):
    _repository = TimeSlotRepository

    async def get_all_by_room_id_and_date_range(
            self,
            room_id: int,
            date_from: datetime,
            date_to: datetime
    ) -> list[tuple[TimeSlot, bool]]:
        return await self._repository.get_all_by_room_id_and_date_range(
            room_id=room_id,
            date_from=date_from,
            date_to=date_to
        )

    async def lock_time_slot_for_booking(self, timeslot_id: int) -> TimeSlot:
        """
        Lock the timeslot for the booking and return timeslot
        :param timeslot_id:
        :return: TimeSlot
        """
        try:
            timeslot, has_active_booking = await self._repository.lock_time_slot_for_booking(timeslot_id=timeslot_id)
        except NoResultFound:
            raise TimeSlotNotFound()

        if has_active_booking:
            raise SlotAlreadyTaken()

        return timeslot
