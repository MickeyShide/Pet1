import asyncio
import hashlib
import json
import logging
from datetime import datetime, timedelta, UTC
from decimal import Decimal
from time import perf_counter
from typing import Any, Awaitable, Callable, List, Tuple, TypeVar
from uuid import UUID

from sqlalchemy.exc import IntegrityError

from app.celery_app.manager import CeleryManager
from app.config import settings
from app.db.base import new_session
from app.models import Booking, TimeSlot
from app.models.room import TimeSlotType, Room
from app.models.timeslot import TimeSlotStatus
from app.schemas import BaseSchema
from app.schemas.booking import (
    SBookingCreate,
    SBookingCreateFlexible,
    SBookingFilters,
    SBookingOut,
    SBookingOutAfterCreate,
    SBookingOutWithTimeslots,
)
from app.schemas.timeslot import STimeSlotFilters, STimeSlotOut
from app.services.booking import BookingService
from app.services.business.base import BaseBusinessService
from app.services.room import RoomService
from app.services.timeslot import TimeSlotService
from app.observability.metrics import (
    dec_business_operation_in_progress,
    inc_business_operation_in_progress,
    observe_business_operation_duration,
    observe_booking_cancel,
    observe_booking_conflict,
    observe_booking_create,
    observe_idempotency_conflict,
    observe_idempotency_reuse,
)
from app.overload import overload_protected
from app.utils.cache import CacheService
from app.utils.err.booking import (
    BookingIdempotencyInProgress,
    BookingIdempotencyKeyConflict,
    SlotAlreadyTaken,
)
from app.utils.err.timeslot import InvalidTimeSlot
from app.utils.redis import get_redis


TBookingResult = TypeVar("TBookingResult", bound=BaseSchema)
logger = logging.getLogger("app.business.bookings")


class BookingsBusinessService(BaseBusinessService):
    booking_service: BookingService
    timeslot_service: TimeSlotService
    room_service: RoomService

    @staticmethod
    def _build_fingerprint(*, operation: str, user_id: int, payload: dict[str, Any]) -> str:
        canonical_payload = json.dumps(
            {
                "operation": operation,
                "user_id": user_id,
                "payload": payload,
            },
            sort_keys=True,
            separators=(",", ":"),
            default=str,
        )
        return hashlib.sha256(canonical_payload.encode("utf-8")).hexdigest()

    @staticmethod
    def _build_idempotency_storage_key(*, user_id: int, idempotency_key: UUID) -> str:
        return f"idempotency:booking:{user_id}:{idempotency_key}"

    @staticmethod
    def _parse_idempotency_state(raw_value: Any) -> dict[str, Any] | None:
        if raw_value is None:
            return None

        if isinstance(raw_value, bytes):
            try:
                raw_value = raw_value.decode("utf-8")
            except Exception:
                return None

        try:
            parsed = json.loads(raw_value)
        except Exception:
            return None

        if not isinstance(parsed, dict):
            return None

        return parsed

    async def _idempotency_try_claim(
            self,
            *,
            storage_key: str,
            fingerprint: str,
    ) -> bool | None:
        try:
            redis = await get_redis()
            result = await redis.set(
                storage_key,
                json.dumps({"status": "in_progress", "fingerprint": fingerprint}),
                ex=settings.BOOKING_IDEMPOTENCY_TTL_SECONDS,
                nx=True,
            )
            return bool(result)
        except Exception:
            return None

    async def _idempotency_get_state(self, storage_key: str) -> dict[str, Any] | None:
        try:
            redis = await get_redis()
            return self._parse_idempotency_state(await redis.get(storage_key))
        except Exception:
            return None

    async def _idempotency_set_completed(
            self,
            *,
            storage_key: str,
            fingerprint: str,
            response_payload: dict[str, Any],
    ) -> bool:
        try:
            redis = await get_redis()
            await redis.set(
                storage_key,
                json.dumps(
                    {
                        "status": "completed",
                        "fingerprint": fingerprint,
                        "response": response_payload,
                    }
                ),
                ex=settings.BOOKING_IDEMPOTENCY_TTL_SECONDS,
            )
            return True
        except Exception:
            return False

    async def _idempotency_delete(self, storage_key: str) -> None:
        try:
            redis = await get_redis()
            await redis.delete(storage_key)
        except Exception:
            return

    async def _idempotent_call(
            self,
            *,
            operation: str,
            payload: dict[str, Any],
            idempotency_key: UUID | None,
            result_model: type[TBookingResult],
            fn: Callable[[], Awaitable[TBookingResult]],
    ) -> TBookingResult:
        if idempotency_key is None or self.user_id is None:
            return await fn()

        fingerprint = self._build_fingerprint(
            operation=operation,
            user_id=self.user_id,
            payload=payload,
        )
        storage_key = self._build_idempotency_storage_key(
            user_id=self.user_id,
            idempotency_key=idempotency_key,
        )

        claim_result = await self._idempotency_try_claim(
            storage_key=storage_key,
            fingerprint=fingerprint,
        )

        # редис упал - работаем как без него
        if claim_result is None:
            return await fn()

        # ключ есть в редисе
        if not claim_result:
            poll_interval = max(0.01, settings.BOOKING_IDEMPOTENCY_POLL_SECONDS)
            wait_seconds = max(0.0, settings.BOOKING_IDEMPOTENCY_WAIT_SECONDS)
            attempts = max(1, int(wait_seconds / poll_interval) + 1)

            for _ in range(attempts):
                state = await self._idempotency_get_state(storage_key)
                if state is None:
                    await asyncio.sleep(poll_interval)
                    continue

                if state.get("fingerprint") != fingerprint:
                    # Key mismatch.
                    observe_idempotency_conflict(source="service", operation=operation, reason="payload_mismatch")
                    logger.info(
                        "idempotency_conflict",
                        extra={
                            "event": "idempotency_conflict",
                            "operation": operation,
                            "idempotency_key": str(idempotency_key),
                            "error_code": "idempotency_payload_mismatch",
                        },
                    )
                    raise BookingIdempotencyKeyConflict()

                if state.get("status") == "completed":
                    response_payload = state.get("response")
                    if isinstance(response_payload, dict):
                        # Cache hit.
                        observe_idempotency_reuse(source="service", operation=operation)
                        logger.info(
                            "idempotency_reused",
                            extra={
                                "event": "idempotency_reused",
                                "operation": operation,
                                "idempotency_key": str(idempotency_key),
                                "booking_id": response_payload.get("id"),
                                "timeslot_id": response_payload.get("timeslot_id"),
                            },
                        )
                        return result_model.model_validate(response_payload)
                    break

                await asyncio.sleep(poll_interval)

            # Still running.
            observe_idempotency_conflict(source="service", operation=operation, reason="in_progress")
            logger.info(
                "idempotency_conflict",
                extra={
                    "event": "idempotency_conflict",
                    "operation": operation,
                    "idempotency_key": str(idempotency_key),
                    "error_code": "idempotency_in_progress",
                },
            )
            raise BookingIdempotencyInProgress()

        try:
            result = await fn()
        except Exception:
            await self._idempotency_delete(storage_key)
            raise

        completed = await self._idempotency_set_completed(
            storage_key=storage_key,
            fingerprint=fingerprint,
            response_payload=result.model_dump(mode="json"),
        )
        if not completed:
            await self._idempotency_delete(storage_key)

        return result

    async def _create_booking_impl(self, booking_data: SBookingCreate) -> SBookingOutAfterCreate:
        # In-flight op.
        operation = "booking_create"
        started_at = perf_counter()
        result_label = "error"
        inc_business_operation_in_progress(operation)
        try:
            try:
                timeslot: TimeSlot = await self.timeslot_service.lock_time_slot_for_booking(booking_data.timeslot_id)
            except SlotAlreadyTaken:
                # Slot clash.
                result_label = "conflict"
                observe_booking_create(result="conflict", source="service", operation="create")
                observe_booking_conflict(source="service", operation="create", reason="slot_taken")
                logger.info(
                    "booking_conflict",
                    extra={
                        "event": "booking_conflict",
                        "timeslot_id": booking_data.timeslot_id,
                        "error_code": "slot_already_taken",
                    },
                )
                raise

            try:
                new_booking: Booking = await self.booking_service.create(
                    user_id=self.user_id,
                    room_id=timeslot.room_id,
                    timeslot_id=timeslot.id,
                    total_price=timeslot.base_price,
                    expires_at=datetime.now(UTC) + timedelta(seconds=settings.BOOKING_EXPIRE_SECONDS),
                )
            except IntegrityError:
                result_label = "conflict"
                observe_booking_create(result="conflict", source="service", operation="create")
                observe_booking_conflict(source="service", operation="create", reason="slot_taken")
                logger.info(
                    "booking_conflict",
                    extra={
                        "event": "booking_conflict",
                        "timeslot_id": booking_data.timeslot_id,
                        "error_code": "slot_already_taken",
                    },
                )
                raise SlotAlreadyTaken()

            await CeleryManager.expire_booking(booking=new_booking)
            await CacheService().invalidate_timeslots_by_room_id(room_id=timeslot.room_id)

            # Success path.
            result_label = "success"
            observe_booking_create(result="success", source="service", operation="create")
            logger.info(
                "booking_created",
                extra={
                    "event": "booking_created",
                    "operation": operation,
                    "booking_id": new_booking.id,
                    "timeslot_id": new_booking.timeslot_id,
                },
            )
            return SBookingOutAfterCreate.from_model(new_booking)
        finally:
            duration_seconds = perf_counter() - started_at
            observe_business_operation_duration(
                operation=operation,
                result=result_label,
                duration_seconds=duration_seconds,
            )
            if duration_seconds >= settings.OBS_SLOW_BUSINESS_OPERATION_SECONDS:
                logger.warning(
                    "business_operation_slow",
                    extra={
                        "event": "business_operation_slow",
                        "operation": operation,
                        "duration_ms": round(duration_seconds * 1000, 3),
                        "threshold_ms": round(settings.OBS_SLOW_BUSINESS_OPERATION_SECONDS * 1000, 3),
                        "result": result_label,
                        "timeslot_id": booking_data.timeslot_id,
                        "anomaly_type": "slow_business_operation",
                    },
                )
            dec_business_operation_in_progress(operation)

    async def _create_booking_flexible_impl(self, booking_data: SBookingCreateFlexible) -> SBookingOutWithTimeslots:
        # In-flight op.
        operation = "booking_create_flexible"
        started_at = perf_counter()
        result_label = "error"
        inc_business_operation_in_progress(operation)
        try:
            room = await self.room_service.get_one_by_id(booking_data.room_id)

            # checks: timeslot type IS flexible, timeslot datetimes is correct
            await self.room_service.check_flexible_booking(room=room, booking_data=booking_data)

            # get timeslot price
            base_price: Decimal = await self.room_service.get_price_quote(booking_data=booking_data)

            # try to create timeslot
            try:
                new_slot: TimeSlot = await self.timeslot_service.create(
                    room_id=booking_data.room_id,
                    start_datetime=booking_data.start_datetime,
                    end_datetime=booking_data.end_datetime,
                    base_price=base_price,
                )
            except IntegrityError:
                # Slot clash.
                result_label = "conflict"
                observe_booking_create(result="conflict", source="service", operation="create_flexible")
                observe_booking_conflict(source="service", operation="create_flexible", reason="invalid_timeslot")
                logger.info(
                    "booking_conflict",
                    extra={
                        "event": "booking_conflict",
                        "timeslot_id": None,
                        "error_code": "flexible_timeslot_conflict",
                    },
                )
                raise InvalidTimeSlot()

            # lock the timeslot for the booking
            try:
                timeslot: TimeSlot = await self.timeslot_service.lock_time_slot_for_booking(new_slot.id)
            except SlotAlreadyTaken:
                # Slot clash.
                result_label = "conflict"
                observe_booking_create(result="conflict", source="service", operation="create_flexible")
                observe_booking_conflict(source="service", operation="create_flexible", reason="slot_taken")
                logger.info(
                    "booking_conflict",
                    extra={
                        "event": "booking_conflict",
                        "timeslot_id": new_slot.id,
                        "error_code": "slot_already_taken",
                    },
                )
                raise

            # create booking
            try:
                new_booking: Booking = await self.booking_service.create(
                    user_id=self.user_id,
                    room_id=timeslot.room_id,
                    timeslot_id=timeslot.id,
                    total_price=timeslot.base_price,
                    expires_at=datetime.now(UTC) + timedelta(seconds=settings.BOOKING_EXPIRE_SECONDS),
                )
                new_booking.room = room
            except IntegrityError:
                # timeslot has active booking
                result_label = "conflict"
                observe_booking_create(result="conflict", source="service", operation="create_flexible")
                observe_booking_conflict(source="service", operation="create_flexible", reason="slot_taken")
                logger.info(
                    "booking_conflict",
                    extra={
                        "event": "booking_conflict",
                        "timeslot_id": new_slot.id,
                        "error_code": "slot_already_taken",
                    },
                )
                raise SlotAlreadyTaken()

            # task to expire booking and timeslot
            await CeleryManager.expire_booking(booking=new_booking)

            # invalidate timeslots cache
            await CacheService().invalidate_timeslots_by_room_id(room_id=timeslot.room_id)

            # Success path.
            result_label = "success"
            observe_booking_create(result="success", source="service", operation="create_flexible")
            logger.info(
                "booking_created",
                extra={
                    "event": "booking_created",
                    "operation": operation,
                    "booking_id": new_booking.id,
                    "timeslot_id": new_booking.timeslot_id,
                },
            )
            return SBookingOutWithTimeslots(
                booking=SBookingOut.from_model(new_booking),
                timeslot=STimeSlotOut.from_model(timeslot),
            )
        finally:
            duration_seconds = perf_counter() - started_at
            observe_business_operation_duration(
                operation=operation,
                result=result_label,
                duration_seconds=duration_seconds,
            )
            if duration_seconds >= settings.OBS_SLOW_BUSINESS_OPERATION_SECONDS:
                logger.warning(
                    "business_operation_slow",
                    extra={
                        "event": "business_operation_slow",
                        "operation": operation,
                        "duration_ms": round(duration_seconds * 1000, 3),
                        "threshold_ms": round(settings.OBS_SLOW_BUSINESS_OPERATION_SECONDS * 1000, 3),
                        "result": result_label,
                        "room_id": booking_data.room_id,
                        "anomaly_type": "slow_business_operation",
                    },
                )
            dec_business_operation_in_progress(operation)

    @overload_protected("booking_create")
    @new_session()
    async def create_booking(
            self,
            booking_data: SBookingCreate,
            idempotency_key: UUID | None = None,
    ) -> SBookingOutAfterCreate:
        return await self._idempotent_call(
            operation="create_booking",
            payload={"timeslot_id": booking_data.timeslot_id},
            idempotency_key=idempotency_key,
            result_model=SBookingOutAfterCreate,
            fn=lambda: self._create_booking_impl(booking_data),
        )

    @overload_protected("booking_create_flexible")
    @new_session()
    async def create_booking_flexible(
            self,
            booking_data: SBookingCreateFlexible,
            idempotency_key: UUID | None = None,
    ) -> SBookingOutWithTimeslots:
        return await self._idempotent_call(
            operation="create_booking_flexible",
            payload={
                "room_id": booking_data.room_id,
                "start_datetime": booking_data.start_datetime.isoformat(),
                "end_datetime": booking_data.end_datetime.isoformat(),
            },
            idempotency_key=idempotency_key,
            result_model=SBookingOutWithTimeslots,
            fn=lambda: self._create_booking_flexible_impl(booking_data),
        )

    @new_session(readonly=True)
    async def get_my_bookings(
            self,
            booking_filters: SBookingFilters | None = None,
            timeslot_filters: STimeSlotFilters | None = None,
    ) -> List[SBookingOutWithTimeslots]:
        bookings_with_timeslots: List[Tuple[Booking, TimeSlot]] = (
            await self.booking_service.get_all_bookings_with_timeslots(
                user_id=self.user_id,
                booking_filters=booking_filters,
                timeslot_filters=timeslot_filters,
            )
        )

        return [
            SBookingOutWithTimeslots(
                booking=SBookingOut.from_model(booking),
                timeslot=STimeSlotOut.from_model(timeslot),
            )
            for booking, timeslot in bookings_with_timeslots
        ]

    @new_session(readonly=True)
    async def get_booking_by_id(self, booking_id: int) -> SBookingOutWithTimeslots:
        booking, timeslot = await self.booking_service.get_booking_with_timeslots_by_id(
            user_id=self.user_id, booking_id=booking_id, is_admin=self.admin
        )

        return SBookingOutWithTimeslots(
            booking=SBookingOut.from_model(booking),
            timeslot=STimeSlotOut.from_model(timeslot),
        )

    @new_session()
    async def cancel_booking(self, booking_id: int) -> bool:
        # In-flight op.
        operation = "booking_cancel"
        started_at = perf_counter()
        result_label = "error"
        inc_business_operation_in_progress(operation)
        try:
            booking: Booking = await self.booking_service.get_one_by_id(booking_id)
            result: bool = await self.booking_service.cancel_booking(
                booking_id=booking_id,
                user_id=self.user_id,
                is_admin=self.admin,
            )
            if result:
                room: Room = await self.room_service.get_one_by_id(booking.room_id)
                if room.time_slot_type == TimeSlotType.FLEXIBLE:
                    await self.timeslot_service.update_by_id(
                        booking.timeslot_id,
                        status=TimeSlotStatus.CANCELED,
                    )
                # invalidate timeslots cache
                await CacheService().invalidate_timeslots_by_room_id(room_id=room.id)

                result_label = "success"
                observe_booking_cancel(result="success", source="service", operation="cancel")
                logger.info(
                    "booking_canceled",
                    extra={
                        "event": "booking_canceled",
                        "operation": operation,
                        "booking_id": booking_id,
                        "timeslot_id": booking.timeslot_id,
                    },
                )
            else:
                # Cancel failed.
                result_label = "failed"
                observe_booking_cancel(result="failed", source="service", operation="cancel")
            return result
        finally:
            duration_seconds = perf_counter() - started_at
            observe_business_operation_duration(
                operation=operation,
                result=result_label,
                duration_seconds=duration_seconds,
            )
            if duration_seconds >= settings.OBS_SLOW_BUSINESS_OPERATION_SECONDS:
                logger.warning(
                    "business_operation_slow",
                    extra={
                        "event": "business_operation_slow",
                        "operation": operation,
                        "booking_id": booking_id,
                        "duration_ms": round(duration_seconds * 1000, 3),
                        "threshold_ms": round(settings.OBS_SLOW_BUSINESS_OPERATION_SECONDS * 1000, 3),
                        "result": result_label,
                        "anomaly_type": "slow_business_operation",
                    },
                )
            dec_business_operation_in_progress(operation)
