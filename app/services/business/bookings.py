import asyncio
import hashlib
import json
from datetime import datetime, timedelta, UTC
from decimal import Decimal
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
from app.utils.cache import CacheService
from app.utils.err.booking import (
    BookingIdempotencyInProgress,
    BookingIdempotencyKeyConflict,
    SlotAlreadyTaken,
)
from app.utils.err.timeslot import InvalidTimeSlot
from app.utils.redis import get_redis


TBookingResult = TypeVar("TBookingResult", bound=BaseSchema)


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
                    raise BookingIdempotencyKeyConflict()

                if state.get("status") == "completed":
                    response_payload = state.get("response")
                    if isinstance(response_payload, dict):
                        return result_model.model_validate(response_payload)
                    break

                await asyncio.sleep(poll_interval)

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
        timeslot: TimeSlot = await self.timeslot_service.lock_time_slot_for_booking(booking_data.timeslot_id)

        try:
            new_booking: Booking = await self.booking_service.create(
                user_id=self.user_id,
                room_id=timeslot.room_id,
                timeslot_id=timeslot.id,
                total_price=timeslot.base_price,
                expires_at=datetime.now(UTC) + timedelta(seconds=settings.BOOKING_EXPIRE_SECONDS),
            )
        except IntegrityError:
            raise SlotAlreadyTaken()

        await CeleryManager.expire_booking(booking=new_booking)

        await CacheService().invalidate_timeslots_by_room_id(room_id=timeslot.room_id)

        return SBookingOutAfterCreate.from_model(new_booking)

    async def _create_booking_flexible_impl(self, booking_data: SBookingCreateFlexible) -> SBookingOutWithTimeslots:
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
            raise InvalidTimeSlot()

        # lock the timeslot for the booking
        timeslot: TimeSlot = await self.timeslot_service.lock_time_slot_for_booking(new_slot.id)

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
            raise SlotAlreadyTaken()

        # task to expire booking and timeslot
        await CeleryManager.expire_booking(booking=new_booking)

        # invalidate timeslots cache
        await CacheService().invalidate_timeslots_by_room_id(room_id=timeslot.room_id)

        return SBookingOutWithTimeslots(
            booking=SBookingOut.from_model(new_booking),
            timeslot=STimeSlotOut.from_model(timeslot),
        )

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
        return result
