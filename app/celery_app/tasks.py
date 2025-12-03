from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import update

from app.celery_app.app import celery_app
from app.db.base import async_session_maker, init_engine
from app.models.booking import Booking, BookingStatus
from app.utils.cache.cache_service import CacheService
from app.utils.cache import keys as cache_keys


async def _expire_booking(booking_id: int) -> dict[str, Any]:
    """
    Async logic for expiring a booking:
    - if status is PENDING_PAYMENTS and expires_at <= now -> set EXPIRED
    - invalidate timeslot cache for the room
    - enqueue notification
    """
    if async_session_maker is None:
        init_engine(echo=False)

    if async_session_maker is None:
        return {"booking_id": booking_id, "status": "skipped_no_engine"}

    async with async_session_maker() as session:
        try:
            stmt = (
                update(Booking)
                .where(Booking.id == booking_id)
                .where(Booking.status == BookingStatus.PENDING_PAYMENTS)
                .where(Booking.expires_at <= datetime.now(timezone.utc))
                .values(status=BookingStatus.EXPIRED)
                .returning(Booking.id, Booking.room_id, Booking.status)
            )
            res = await session.execute(stmt)
            row = res.one_or_none()
            if row is None:
                await session.rollback()
                return {"booking_id": booking_id, "status": "skipped_not_pending_or_not_expired"}

            await session.commit()
            booking_id_db, room_id, status = row

            # Invalidate cached timeslots for the room
            await CacheService().delete_pattern(cache_keys.timeslots_room_prefix(room_id))

            return {"booking_id": booking_id_db, "status": status}
        except Exception as exc:
            try:
                await session.rollback()
            except Exception:
                pass
            return {"booking_id": booking_id, "status": "error", "detail": str(exc)}


@celery_app.task(name="app.bookings.expire_booking")
def expire_booking(booking_id: int) -> dict[str, Any]:
    """
    Celery entrypoint for expiring bookings according to the spec.
    """
    return asyncio.run(_expire_booking(booking_id))
