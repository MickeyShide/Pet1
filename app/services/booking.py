from app.models import Booking, TimeSlot
from app.repositories.booking import BookingRepository
from app.schemas.booking import SBookingFilters
from app.services.base import BaseService


class BookingService(BaseService[Booking]):
    _repository = BookingRepository

    async def get_all_bookings_with_timeslots(
            self,
            user_id: int,
            filters: SBookingFilters | None = None,
    ) -> list[tuple[Booking, TimeSlot]]:
        return await self._repository.get_all_bookings_with_timeslots(user_id=user_id, filters=filters)
