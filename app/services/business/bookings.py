from datetime import datetime, timedelta, UTC

from app.db.base import new_session
from app.models import Booking
from app.schemas.booking import SBookingCreate, SBookingOut, SBookingOutAfterCreate
from app.services.booking import BookingService
from app.services.business.base import BaseBusinessService
from app.services.timeslot import TimeSlotService


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
            expires_at=datetime.now(UTC) + timedelta(minutes=15),
        )

        return SBookingOutAfterCreate.from_model(new_booking)
