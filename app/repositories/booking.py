from sqlalchemy import select, update

from app.models import Booking, TimeSlot
from app.models.booking import BookingStatus
from app.repositories.base import BaseRepository
from app.schemas.booking import SBookingFilters
from app.schemas.timeslot import STimeSlotFilters


class BookingRepository(BaseRepository[Booking]):
    _model_cls = Booking

    async def get_all_bookings_with_timeslots(
            self,
            user_id: int,
            booking_filters: SBookingFilters | None = None,
            timeslot_filters: STimeSlotFilters | None = None,
    ) -> list[tuple[Booking, TimeSlot]]:
        stmt = (
            select(self._model_cls, TimeSlot)
            .join(TimeSlot, self._model_cls.timeslot_id == TimeSlot.id)
            .where(self._model_cls.user_id == user_id)
        )

        if booking_filters is not None:
            for column, value in booking_filters.model_dump(exclude_unset=True).items():
                if value is not None:
                    stmt = stmt.where(getattr(self._model_cls, column) == value)

        if timeslot_filters is not None:
            if timeslot_filters.start_datetime is not None:
                stmt = stmt.where(TimeSlot.end_datetime >= timeslot_filters.start_datetime)
            if timeslot_filters.end_datetime is not None:
                stmt = stmt.where(TimeSlot.start_datetime <= timeslot_filters.end_datetime)

        stmt = stmt.order_by(self._model_cls.created_at)

        res = await self.session.execute(stmt)

        return [(booking, timeslot) for booking, timeslot in res.all()]

    async def get_booking_with_timeslots_by_id(
            self,
            booking_id: int,
            user_id: int,
            is_admin: bool
    ) -> tuple[Booking, TimeSlot]:
        stmt = (
            select(self._model_cls, TimeSlot)
            .join(TimeSlot, self._model_cls.timeslot_id == TimeSlot.id)
            .where(self._model_cls.id == booking_id)
        )

        if not is_admin:
            stmt = stmt.where(self._model_cls.user_id == user_id)

        res = await self.session.execute(stmt)

        row = res.one()

        return row[0], row[1]  # Booking, TimeSlot
    
    async def cancel_booking(self, booking_id: int, user_id: int, is_admin: bool) -> Booking:
        stmt = (
            update(self._model_cls)
            .where(self._model_cls.id == booking_id)
            .where(self._model_cls.status == BookingStatus.PENDING_PAYMENTS)
            .values(status=BookingStatus.CANCELED)
            .returning(self._model_cls)
        )

        if not is_admin:
            stmt = stmt.where(self._model_cls.user_id == user_id)

        res = await self.session.execute(stmt)

        return res.one()[0]
