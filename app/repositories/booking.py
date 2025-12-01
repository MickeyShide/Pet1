from app.models import Booking
from app.repositories.base import BaseRepository


class BookingRepository(BaseRepository[Booking]):
    _model_cls = Booking

    async def get_all_by_room_id_and_date_range(
            self,
            room_id: int,
            date_from: datetime,
            date_to: datetime,
    ) -> list[tuple[TimeSlot, bool]]:
        ActiveBooking = aliased(Booking, name="active_booking")

        stmt = (
            select(
                self._model_cls,
                # вернёт True, если есть строка брони, иначе False
                (ActiveBooking.id.is_not(None)).label("has_active_booking"),
            )
            .join(
                ActiveBooking,
                and_(
                    ActiveBooking.timeslot_id == self._model_cls.id,
                    ActiveBooking.status.in_(
                        [BookingStatus.PENDING_PAYMENTS, BookingStatus.PAID]
                    ),
                ),
                isouter=True,  # LEFT JOIN
            )
            .where(self._model_cls.room_id == room_id)
            .where(self._model_cls.start_datetime >= date_from)
            .where(self._model_cls.end_datetime <= date_to)
            .order_by(self._model_cls.start_datetime)
        )

        result = await self.session.execute(stmt)
        rows = result.all()  # list[Row[TimeSlot, bool]]

        return [(slot, has_active_booking) for slot, has_active_booking in rows]
