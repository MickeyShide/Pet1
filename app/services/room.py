from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP

from app.models import Room
from app.models.room import TimeSlotType
from app.repositories.room import RoomRepository
from app.services.base import BaseService
from app.utils.err.room import NotFlexibleTimeslotsType, InvalidBookingDuration


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

    @staticmethod
    async def check_flexible_booking(
            room: Room,
            start_datetime: datetime,
            end_datetime: datetime
    ) -> None:
        """
        checks: timeslot type IS flexible, timeslot datetimes is correct
        raises HTTPExceptions
        """

        if room.time_slot_type != TimeSlotType.FLEXIBLE:
            raise NotFlexibleTimeslotsType()

        min_minutes = room.min_booking_duration_minutes
        step_minutes = room.booking_step_minutes
        start = start_datetime
        end = end_datetime
        delta = end - start
        duration_minutes = delta.days * 24 * 60 + delta.seconds // 60
        start_minute_of_day = start.hour * 60 + start.minute

        if (
                start.second != 0
                or start.microsecond != 0
                or end.second != 0
                or end.microsecond != 0
                or delta.microseconds != 0
                or delta.seconds % 60 != 0
                or duration_minutes < min_minutes
                or start_minute_of_day % step_minutes != 0
                or duration_minutes % step_minutes != 0
        ):
            raise InvalidBookingDuration(min_minutes=min_minutes, step_minutes=step_minutes)
