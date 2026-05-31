from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from time import perf_counter
from typing import Any

from sqlalchemy import select, update

from app.celery_app.app import celery_app
from app.config import settings
from app.db import base as db_base
from app.models import Room, TimeSlot
from app.models.booking import Booking, BookingStatus
from app.models.room import TimeSlotType
from app.models.timeslot import TimeSlotStatus
from app.observability.metrics import observe_background_task
from app.utils.cache import keys as cache_keys
from app.utils.cache.cache_service import CacheService

logger = logging.getLogger("app.celery.tasks")


def _parse_scheduled_for(scheduled_for_iso: str | None) -> datetime | None:
    if not scheduled_for_iso:
        return None
    try:
        parsed = datetime.fromisoformat(scheduled_for_iso)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


async def _expire_booking(booking_id: int, scheduled_for_iso: str | None = None) -> dict[str, Any]:
    """
    Async logic for expiring a booking:
    - if status is PENDING_PAYMENTS and expires_at <= now -> set EXPIRED
    - cancel timeslot for flexible rooms
    - invalidate timeslot cache for the room
    - enqueue notification
    """
    started_at = perf_counter()
    result = "error"
    scheduled_for = _parse_scheduled_for(scheduled_for_iso)
    lag_seconds = None
    if scheduled_for is not None:
        lag_seconds = max(0.0, (datetime.now(timezone.utc) - scheduled_for).total_seconds())
    logger.info(
        "booking_expire_task_started",
        extra={
            "event": "booking_expire_task_started",
            "task": "expire_booking",
            "booking_id": booking_id,
            "scheduled_for": scheduled_for.isoformat() if scheduled_for else None,
            "schedule_lag_ms": round(lag_seconds * 1000, 3) if lag_seconds is not None else None,
        },
    )
    try:
        if db_base.async_session_maker is None:
            db_base.init_engine(echo=False)

        if db_base.async_session_maker is None:
            result = "skipped_no_engine"
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
                    result = "skipped_not_due"
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
                result = "success"
                return {"booking_id": booking_id_db, "status": status}
            except asyncio.CancelledError:
                try:
                    await session.rollback()
                except Exception:
                    pass
                result = "cancelled"
                raise
            except Exception as exc:
                try:
                    await session.rollback()
                except Exception:
                    pass
                result = "error"
                return {"booking_id": booking_id, "status": "error", "detail": str(exc)}
    finally:
        duration_seconds = perf_counter() - started_at
        observe_background_task(
            task="expire_booking",
            result=result,
            duration_seconds=duration_seconds,
            lag_seconds=lag_seconds,
        )
        logger.info(
            "booking_expire_task_finished",
            extra={
                "event": "booking_expire_task_finished",
                "task": "expire_booking",
                "booking_id": booking_id,
                "result": result,
                "duration_ms": round(duration_seconds * 1000, 3),
                "schedule_lag_ms": round(lag_seconds * 1000, 3) if lag_seconds is not None else None,
            },
        )
        if lag_seconds is not None and lag_seconds >= settings.OBS_HIGH_BOOKING_EXPIRATION_LAG_SECONDS:
            logger.warning(
                "booking_expire_task_lag_high",
                extra={
                    "event": "booking_expire_task_lag_high",
                    "task": "expire_booking",
                    "booking_id": booking_id,
                    "schedule_lag_ms": round(lag_seconds * 1000, 3),
                    "threshold_ms": round(settings.OBS_HIGH_BOOKING_EXPIRATION_LAG_SECONDS * 1000, 3),
                    "anomaly_type": "background_task_schedule_lag",
                },
            )


@celery_app.task(name="app.bookings.expire_booking")
def expire_booking_task(booking_id: int, scheduled_for_iso: str | None = None) -> dict[str, Any]:
    """
    Celery entrypoint for expiring bookings according to the spec.
    """
    payload = asyncio.run(_expire_booking(booking_id, scheduled_for_iso))
    return payload
