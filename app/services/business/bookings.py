import logging
from datetime import datetime, timedelta, UTC
from typing import List, Tuple

from app.celery_app.tasks import expire_booking
from app.config import settings
from app.db.base import new_session
from app.models import Booking, TimeSlot
from app.schemas.booking import (
    SBookingCreate,
    SBookingFilters,
    SBookingOut,
    SBookingOutAfterCreate,
    SBookingOutWithTimeslots,
)
from app.schemas.timeslot import STimeSlotFilters, STimeSlotOut
from app.services.booking import BookingService
from app.services.business.base import BaseBusinessService
from app.services.timeslot import TimeSlotService
from app.utils.cache import CacheService
from app.utils.cache import keys as cache_keys


class BookingsBusinessService(BaseBusinessService):
    booking_service: BookingService
    timeslot_service: TimeSlotService

    @new_session()
    async def create_booking(self, booking_data: SBookingCreate) -> SBookingOutAfterCreate:
        timeslot = await self.timeslot_service.lock_time_slot_for_booking(booking_data.timeslot_id)

        new_booking: Booking = await self.booking_service.create(
            user_id=self.user_id,
            room_id=timeslot.room_id,
            timeslot_id=timeslot.id,
            total_price=timeslot.base_price,
            expires_at=datetime.now(UTC) + timedelta(seconds=settings.BOOKING_EXPIRE_SECONDS),
        )
        try:
            expire_booking.apply_async(args=[new_booking.id], eta=new_booking.expires_at)
        except Exception as exc:
            ...
            # TODO сюда логгер
        await CacheService().delete_pattern(cache_keys.timeslots_room_prefix(timeslot.room_id))
        return SBookingOutAfterCreate.from_model(new_booking)

    @new_session()
    async def get_my_bookings(
        self,
        booking_filters: SBookingFilters | None = None,
        timeslot_filters: STimeSlotFilters | None = None,
    ) -> List[SBookingOutWithTimeslots]:
        bookings_with_timeslots: List[Tuple[Booking, TimeSlot]] = (
            await self.booking_service.get_all_bookings_with_timeslots(
                user_id=self.user_id,
                booking_filters=booking_filters,
                timeslot_filters=timeslot_filters,
            )
        )

        return [
            SBookingOutWithTimeslots(
                booking=SBookingOut.from_model(booking),
                timeslot=STimeSlotOut.from_model(timeslot),
            )
            for booking, timeslot in bookings_with_timeslots
        ]

    @new_session(readonly=True)
    async def get_booking_by_id(self, booking_id: int) -> SBookingOutWithTimeslots:
        booking, timeslot = await self.booking_service.get_booking_with_timeslots_by_id(
            user_id=self.user_id, booking_id=booking_id, is_admin=self.admin
        )

        return SBookingOutWithTimeslots(
            booking=SBookingOut.from_model(booking),
            timeslot=STimeSlotOut.from_model(timeslot),
        )

    @new_session()
    async def cancel_booking(self, booking_id: int) -> bool:
        booking: Booking = await self.booking_service.get_one_by_id(booking_id)
        result = await self.booking_service.cancel_booking(
            booking_id=booking_id,
            user_id=self.user_id,
            is_admin=self.admin,
        )
        await CacheService().delete_pattern(cache_keys.timeslots_room_prefix(booking.room_id))
        return result
