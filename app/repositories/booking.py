from sqlalchemy import select, and_

from app.models import Booking, TimeSlot
from app.repositories.base import BaseRepository
from app.schemas.booking import SBookingFilters


class BookingRepository(BaseRepository[Booking]):
    _model_cls = Booking

    async def get_all_bookings_with_timeslots(
            self,
            user_id: int,
            filters: SBookingFilters | None = None,
    ) -> list[tuple[Booking, TimeSlot]]:
        stmt = (
            select(self._model_cls, TimeSlot)
            .join(TimeSlot, self._model_cls.timeslot_id == TimeSlot.id)
            .where(self._model_cls.user_id == user_id)
        )

        conditions = []

        if filters is not None:
            # фильтры по букингу
            booking_filters = filters.model_dump(
                exclude={"timeslot_filter"},
                exclude_unset=True,
            )
            if booking_filters:
                stmt = stmt.filter_by(**booking_filters)

            # фильтры по таймслоту
            ts_filter = filters.timeslot_filter
            if ts_filter is not None:
                if ts_filter.start_datetime is not None:
                    # end_datetime таймслота >= фильтра start_datetime
                    conditions.append(TimeSlot.end_datetime >= ts_filter.start_datetime)
                if ts_filter.end_datetime is not None:
                    # start_datetime таймслота <= фильтра end_datetime
                    conditions.append(TimeSlot.start_datetime <= ts_filter.end_datetime)

        if conditions:
            stmt = stmt.where(and_(*conditions))

        stmt = stmt.order_by(self._model_cls.created_at)

        res = await self.session.execute(stmt)

        return [(booking, timeslot) for booking, timeslot in res.all()]
