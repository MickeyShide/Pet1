from sqlalchemy.exc import NoResultFound

from app.models import Booking, TimeSlot
from app.models.booking import BookingStatus
from app.repositories.booking import BookingRepository
from app.schemas.booking import SBookingFilters
from app.schemas.timeslot import STimeSlotFilters
from app.services.base import BaseService
from app.utils.err.base.conflict import ConflictException
from app.utils.err.base.not_found import NotFoundException
from app.utils.err.booking import BookingNotFound


class BookingService(BaseService[Booking]):
    _repository = BookingRepository

    async def get_all_bookings_with_timeslots(
            self,
            user_id: int,
            booking_filters: SBookingFilters | None = None,
            timeslot_filters: STimeSlotFilters | None = None,
    ) -> list[tuple[Booking, TimeSlot]]:
        return await self._repository.get_all_bookings_with_timeslots(
            user_id=user_id,
            booking_filters=booking_filters,
            timeslot_filters=timeslot_filters,
        )

    async def get_booking_with_timeslots_by_id(
            self,
            booking_id: int,
            user_id: int,
            is_admin: bool
    ) -> tuple[Booking, TimeSlot]:
        try:
            return await self._repository.get_booking_with_timeslots_by_id(
                booking_id=booking_id,
                user_id=user_id,
                is_admin=is_admin
            )
        except NoResultFound:
            raise NotFoundException(f"Booking with id {booking_id} not found")

    async def set_booking_paid(self, booking_id: int) -> Booking:
        try:
            return await self._repository.set_booking_paid(booking_id=booking_id)
        except NoResultFound:
            raise BookingNotFound()

    async def cancel_booking(self, booking_id: int, user_id: int, is_admin: bool) -> bool:
        try:
            old_booking_status: BookingStatus = await self._repository.check_booking_status(
                booking_id=booking_id, user_id=user_id, is_admin=is_admin
            )

            if old_booking_status is not BookingStatus.PENDING_PAYMENTS:
                raise ConflictException(f"Booking with id {booking_id} status: {old_booking_status.value}")

            updated_booking: Booking = await self._repository.cancel_booking(
                booking_id=booking_id, user_id=user_id, is_admin=is_admin
            )

            if updated_booking.status == BookingStatus.CANCELED:
                return True

            return False
        except NoResultFound:
            raise NotFoundException(f"Booking with id {booking_id} not found")
