from datetime import datetime

from sqlalchemy import select, and_
from sqlalchemy.exc import NoResultFound
from sqlalchemy.orm import aliased

from app.models import Booking
from app.models.booking import BookingStatus
from app.models.timeslot import TimeSlot
from app.repositories.base import BaseRepository


class TimeSlotRepository(BaseRepository[TimeSlot]):
    _model_cls = TimeSlot

    async def lock_time_slot_for_booking(self, timeslot_id) -> tuple[TimeSlot, bool]:
        """
        Lock the timeslot for the booking and return timeslot
        :param timeslot_id:
        :return: timeslot: TimeSlot, has_active_booking: bool
        """
        ActiveBooking = aliased(Booking, name="active_booking")

        stmt = (
            select(
                self._model_cls,
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
            .where(self._model_cls.id == timeslot_id)
            .with_for_update(of=self._model_cls)
        )

        result = await self.session.execute(stmt)
        row = result.one_or_none()  # Row | None

        if row is None:
            raise NoResultFound

        timeslot, has_active_booking = row

        return timeslot, has_active_booking

    async def get_all_by_room_id_and_date_range(
            self,
            room_id: int,
            date_from: datetime,
            date_to: datetime,
    ) -> list[tuple[TimeSlot, bool]]:
        """
        Retrieve all timeslots for a room and a date range, with has_active_booking flag
        :param room_id:
        :param date_from:
        :param date_to:
        :return: list[tuple[TimeSlot, bool]]
        """
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
