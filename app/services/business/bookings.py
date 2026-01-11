from datetime import datetime, timedelta, UTC
from decimal import Decimal
from typing import List, Tuple

from sqlalchemy.exc import IntegrityError

from app.celery_app.manager import CeleryManager
from app.config import settings
from app.db.base import new_session
from app.models import Booking, TimeSlot
from app.models.room import TimeSlotType, Room
from app.models.timeslot import TimeSlotStatus
from app.schemas.booking import (
    SBookingCreate,
    SBookingFilters,
    SBookingOut,
    SBookingOutAfterCreate,
    SBookingOutWithTimeslots, SBookingCreateFlexible,
)
from app.schemas.timeslot import STimeSlotFilters, STimeSlotOut
from app.services.booking import BookingService
from app.services.business.base import BaseBusinessService
from app.services.room import RoomService
from app.services.timeslot import TimeSlotService
from app.utils.cache import CacheService
from app.utils.cache import keys as cache_keys
from app.utils.err.booking import SlotAlreadyTaken
from app.utils.err.timeslot import InvalidTimeSlot


class BookingsBusinessService(BaseBusinessService):
    booking_service: BookingService
    timeslot_service: TimeSlotService
    room_service: RoomService

    @new_session()
    async def create_booking(self, booking_data: SBookingCreate) -> SBookingOutAfterCreate:
        timeslot: TimeSlot = await self.timeslot_service.lock_time_slot_for_booking(booking_data.timeslot_id)

        new_booking: Booking = await self.booking_service.create(
            user_id=self.user_id,
            room_id=timeslot.room_id,
            timeslot_id=timeslot.id,
            total_price=timeslot.base_price,
            expires_at=datetime.now(UTC) + timedelta(seconds=settings.BOOKING_EXPIRE_SECONDS),
        )

        await CeleryManager.expire_booking(booking=new_booking)

        await CacheService().invalidate_timeslots_by_room_id(room_id=timeslot.room_id)

        return SBookingOutAfterCreate.from_model(new_booking)

    @new_session()
    async def create_booking_flexible(self, booking_data: SBookingCreateFlexible) -> SBookingOutWithTimeslots:

        room = await self.room_service.get_one_by_id(booking_data.room_id)

        # checks: timeslot type IS flexible, timeslot datetimes is correct
        await self.room_service.check_flexible_booking(room=room,booking_data=booking_data)

        # get timeslot price
        base_price: Decimal = await self.room_service.get_price_quote(booking_data=booking_data)

        # try to create timeslot
        try:
            new_slot: TimeSlot = await self.timeslot_service.create(
                room_id=booking_data.room_id,
                start_datetime=booking_data.start_datetime,
                end_datetime=booking_data.end_datetime,
                base_price=base_price,
            )
        except IntegrityError:
            raise InvalidTimeSlot()

        # lock the timeslot for the booking
        timeslot: TimeSlot = await self.timeslot_service.lock_time_slot_for_booking(new_slot.id)

        # create booking
        try:
            new_booking: Booking = await self.booking_service.create(
                user_id=self.user_id,
                room_id=timeslot.room_id,
                timeslot_id=timeslot.id,
                total_price=timeslot.base_price,
                expires_at=datetime.now(UTC) + timedelta(seconds=settings.BOOKING_EXPIRE_SECONDS),
            )
            new_booking.room = room
        except IntegrityError as e:
            # timeslot has active booking
            raise SlotAlreadyTaken()

        # task to expire booking and timeslot
        await CeleryManager.expire_booking(booking=new_booking)

        # invalidate timeslots cache
        await CacheService().invalidate_timeslots_by_room_id(room_id=timeslot.room_id)

        return SBookingOutWithTimeslots(
            booking=SBookingOut.from_model(new_booking),
            timeslot=STimeSlotOut.from_model(timeslot),
        )

    @new_session(readonly=True)
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
        result: bool = await self.booking_service.cancel_booking(
            booking_id=booking_id,
            user_id=self.user_id,
            is_admin=self.admin,
        )
        if result:
            room: Room = await self.room_service.get_one_by_id(booking.room_id)
            if room.time_slot_type == TimeSlotType.FLEXIBLE:
                await self.timeslot_service.update_by_id(
                    booking.timeslot_id,
                    status=TimeSlotStatus.CANCELED,
                )
            # invalidate timeslots cache
            await CacheService().invalidate_timeslots_by_room_id(room_id=room.id)
        return result
