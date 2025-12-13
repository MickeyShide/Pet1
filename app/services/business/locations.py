from typing import List

from app.db.base import new_session
from app.models import Location, Room
from app.config import settings
from app.schemas.location import SLocationOut, SLocationCreate, SLocationUpdate
from app.schemas.room import SRoomOut
from app.services.business.base import BaseBusinessService
from app.services.location import LocationService
from app.services.room import RoomService
from app.utils.cache import CacheService, keys


class LocationBusinessService(BaseBusinessService):
    location_service: LocationService
    room_service: RoomService

    @new_session(readonly=True)
    async def get_all(self) -> list[SLocationOut]:

        cache = CacheService[list[SLocationOut]](model=SLocationOut, collection=True)
        cache_key = keys.locations_all()
        cached = await cache.try_get(cache_key)
        if cached is not None:
            return cached

        locations: List[Location] = await self.location_service.get_all()
        retult: list[SLocationOut] = [SLocationOut.from_model(location) for location in locations]
        await cache.try_set(cache_key, retult, ttl=settings.LOCATION_CACHE_TTL_SECONDS)

        return retult

    @new_session(readonly=True)
    async def get_by_id(self, location_id: int) -> SLocationOut:
        location: Location = await self.location_service.get_one_by_id(location_id)
        return SLocationOut.from_model(location)

    @new_session()
    async def create_location(self, location_data: SLocationCreate) -> SLocationOut:
        location: Location = await self.location_service.create(**location_data.model_dump())
        await CacheService().delete_pattern(keys.locations_all())
        return SLocationOut.from_model(location)

    @new_session()
    async def update_by_id(self, location_id: int, location_data: SLocationUpdate) -> SLocationOut:
        location: Location = await self.location_service.update_by_id(
            location_id,
            **location_data.model_dump(exclude_unset=True)
        )
        await CacheService().delete_pattern(keys.locations_all())
        return SLocationOut.from_model(location)

    @new_session()
    async def delete_by_id(self, location_id: int) -> None:
        await self.location_service.delete_by_id(location_id)
        await CacheService().delete_pattern(keys.locations_all())

    @new_session(readonly=True)
    async def get_rooms_by_location_id(self, location_id: int) -> List[SRoomOut]:
        rooms: List[Room] = await self.room_service.find_all_by_filters(location_id=location_id)
        return [SRoomOut.from_model(room) for room in rooms]
