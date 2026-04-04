from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select, update

from app.celery_app.app import celery_app
from app.db import base as db_base
from app.models import Room, TimeSlot
from app.models.booking import Booking, BookingStatus
from app.models.room import TimeSlotType
from app.models.timeslot import TimeSlotStatus
from app.utils.cache import keys as cache_keys
from app.utils.cache.cache_service import CacheService


async def _expire_booking(booking_id: int) -> dict[str, Any]:
    """
    Async logic for expiring a booking:
    - if status is PENDING_PAYMENTS and expires_at <= now -> set EXPIRED
    - cancel timeslot for flexible rooms
    - invalidate timeslot cache for the room
    - enqueue notification
    """
    if db_base.async_session_maker is None:
        db_base.init_engine(echo=False)

    if db_base.async_session_maker is None:
        return {"booking_id": booking_id, "status": "skipped_no_engine"}

    async with db_base.async_session_maker() as session:
        try:
            stmt = (
                update(Booking)
                .where(Booking.id == booking_id)
                .where(Booking.status == BookingStatus.PENDING_PAYMENTS)
                .where(Booking.expires_at <= datetime.now(timezone.utc))
                .values(status=BookingStatus.EXPIRED)
                .returning(Booking.id, Booking.room_id, Booking.timeslot_id, Booking.status)
            )
            res = await session.execute(stmt)
            row = res.one_or_none()
            if row is None:
                await session.rollback()
                return {"booking_id": booking_id, "status": "skipped_not_pending_or_not_expired"}

            booking_id_db, room_id, timeslot_id, status = row
            room_type_res = await session.execute(
                select(Room.time_slot_type).where(Room.id == room_id)
            )
            room_time_slot_type = room_type_res.scalar_one_or_none()
            if room_time_slot_type == TimeSlotType.FLEXIBLE:
                await session.execute(
                    update(TimeSlot)
                    .where(TimeSlot.id == timeslot_id)
                    .values(status=TimeSlotStatus.CANCELED)
                )

            await session.commit()

            # Invalidate cached timeslots for the room
            await CacheService().delete_pattern(cache_keys.timeslots_room_prefix(room_id))

            return {"booking_id": booking_id_db, "status": status}
        except asyncio.CancelledError:
            try:
                await session.rollback()
            except Exception:
                pass
            raise
        except Exception as exc:
            try:
                await session.rollback()
            except Exception:
                pass
            return {"booking_id": booking_id, "status": "error", "detail": str(exc)}


@celery_app.task(name="app.bookings.expire_booking")
def expire_booking_task(booking_id: int) -> dict[str, Any]:
    """
    Celery entrypoint for expiring bookings according to the spec.
    """
    payload = asyncio.run(_expire_booking(booking_id))
    return payload
