from datetime import datetime

from sqlalchemy.exc import NoResultFound

from app.models import TimeSlot
from app.models.timeslot import TimeSlotStatus
from app.repositories.timeslot import TimeSlotRepository
from app.services.base import BaseService
from app.utils.err.booking import TimeSlotNotFound, SlotAlreadyTaken, TimeSlotBlocked, TimeSlotCancelled


class TimeSlotService(BaseService[TimeSlot]):
    _repository = TimeSlotRepository

    async def get_all_by_room_id_and_date_range(
            self,
            room_id: int,
            date_from: datetime,
            date_to: datetime,
            include_canceled: bool = True,
    ) -> list[tuple[TimeSlot, bool]]:
        return await self._repository.get_all_by_room_id_and_date_range(
            room_id=room_id,
            date_from=date_from,
            date_to=date_to,
            include_canceled=include_canceled,
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

        if timeslot.status == TimeSlotStatus.BLOCKED:
            raise TimeSlotBlocked()

        if timeslot.status == TimeSlotStatus.CANCELED:
            raise TimeSlotCancelled()

        return timeslot
