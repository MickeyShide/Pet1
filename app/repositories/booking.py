from sqlalchemy import select, and_

from app.models import Booking, TimeSlot
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

        conditions = []

        if booking_filters is not None:
            # фильтры по букингу
            booking_filters = booking_filters.model_dump(
                exclude_unset=True,
            )
            if booking_filters:
                stmt = stmt.filter_by(**booking_filters)
        if timeslot_filters is not None:
            timeslot_filters = timeslot_filters.model_dump(
                exclude_unset=True,
            )
            if timeslot_filters is not None:
                if timeslot_filters.start_datetime is not None:
                    # end_datetime таймслота >= фильтра start_datetime
                    conditions.append(TimeSlot.end_datetime >= timeslot_filters.start_datetime)
                if timeslot_filters.end_datetime is not None:
                    # start_datetime таймслота <= фильтра end_datetime
                    conditions.append(TimeSlot.start_datetime <= timeslot_filters.end_datetime)

        if conditions:
            stmt = stmt.where(and_(*conditions))

        stmt = stmt.order_by(self._model_cls.created_at)

        res = await self.session.execute(stmt)

        return [(booking, timeslot) for booking, timeslot in res.all()]
