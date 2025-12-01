from app.models import Booking, TimeSlot
from app.repositories.booking import BookingRepository
from app.schemas.booking import SBookingFilters
from app.schemas.timeslot import STimeSlotFilters
from app.services.base import BaseService


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
