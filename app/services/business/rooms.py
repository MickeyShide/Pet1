from datetime import datetime
from typing import List

from app.config import settings
from app.db.base import new_session
from app.models import Room
from app.schemas.booking import SBookingCreateFlexible
from app.schemas.room import SRoomOut, SRoomCreate, SRoomUpdate, SRoomOutWithLocation, SRoomFilter
from app.schemas.timeslot import STimeSlotDateRange, STimeSlotOutWithBookingStatus, STimeSlotCreate, STimeSlotOut, \
    SPriceQuoteOut
from app.services.business.base import BaseBusinessService
from app.services.location import LocationService
from app.services.room import RoomService
from app.services.timeslot import TimeSlotService
from app.utils.cache import keys as cache_keys
from app.utils.cache.cache_service import CacheService


class RoomBusinessService(BaseBusinessService):
    location_service: LocationService
    room_service: RoomService
    timeslots_service: TimeSlotService

    @new_session(readonly=True)
    async def get_all_with_location(
            self,
            filters: SRoomFilter,
            page: int,
            limit: int,
    ) -> list[SRoomOutWithLocation]:
        rooms: list[Room] = await self.room_service.get_all_with_location(filters, page, limit)

        return [SRoomOutWithLocation.from_model(room) for room in rooms]

    @new_session()
    async def create_by_location_id(self, location_id: int, room_data: SRoomCreate) -> SRoomOut:
        await self.location_service.get_one_by_id(location_id)
        room: Room = await self.room_service.create(location_id=location_id, **room_data.to_dict())
        room = await self.room_service.get_one_by_id(room.id)
        return SRoomOut.from_model(room)

    @new_session(readonly=True)
    async def get_by_id(self, room_id: int) -> SRoomOut:
        room: Room = await self.room_service.get_one_by_id(room_id)
        return SRoomOut.from_model(room)

    @new_session()
    async def update_by_id(self, room_id: int, room_data: SRoomUpdate) -> SRoomOut:
        await self.room_service.update_by_id(
            room_id,
            **room_data.to_dict()
        )
        room: Room = await self.room_service.get_one_by_id(room_id)
        return SRoomOut.from_model(room)

    @new_session()
    async def delete_by_id(self, room_id: int) -> None:
        await self.room_service.delete_by_id(room_id)

    @new_session(readonly=True)
    async def get_timeslots_by_date_range_with_booking_flag(
            self,
            room_id: int,
            date_range: STimeSlotDateRange
    ) -> List[STimeSlotOutWithBookingStatus]:
        await self.room_service.get_one_by_id(room_id)

        cache = CacheService[List[STimeSlotOutWithBookingStatus]](model=STimeSlotOutWithBookingStatus, collection=True)
        cache_key = cache_keys.timeslots_by_room_and_range(
            room_id=room_id, date_from=date_range.date_from, date_to=date_range.date_to
        )
        cached: List[STimeSlotOutWithBookingStatus] = await cache.try_get(cache_key)

        if cached is not None:
            timeslot_dicts = cached
        else:
            print("NOT CACHED")
            timeslots_with_booking = await self.timeslots_service.get_all_by_room_id_and_date_range(
                room_id=room_id,
                date_from=date_range.date_from,
                date_to=date_range.date_to,
                include_canceled=False,
            )
            timeslot_dicts: List[STimeSlotOutWithBookingStatus] = [
                STimeSlotOutWithBookingStatus(
                    **STimeSlotOut.from_model(slot).to_dict(),
                    has_active_booking=has_active_booking,
                )
                for slot, has_active_booking in timeslots_with_booking
            ]
            # CACHE! Key: timeslots:{room_id}:{date_from}:{date_to} TTL: 30s
            await cache.try_set(
                cache_key,
                timeslot_dicts,
                ttl=settings.TIMESLOT_CACHE_TTL_SECONDS,
            )

        return timeslot_dicts

    @new_session()
    async def create_timeslot(self, room_id: int, timeslot_data: STimeSlotCreate) -> STimeSlotOut:
        await self.room_service.get_one_by_id(room_id)
        new_slot = await self.timeslots_service.create(room_id=room_id, **timeslot_data.to_dict())
        await CacheService().delete_pattern(cache_keys.timeslots_room_prefix(room_id))
        return STimeSlotOut.from_model(new_slot)

    @new_session(readonly=True)
    async def get_price_quote(self, room_id: int, date_from: datetime, date_to: datetime) -> SPriceQuoteOut:

        room = await self.room_service.get_one_by_id(room_id)

        # checks: timeslot type IS flexible, timeslot datetimes is correct
        await self.room_service.check_flexible_booking(
            room=room,
            start_datetime=date_from,
            end_datetime=date_to
        )

        price = await self.room_service.get_price_quote(room_id, date_from, date_to)

        return SPriceQuoteOut(price=price)
