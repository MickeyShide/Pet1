from typing import List, Any, Coroutine

from app.db.base import new_session
from app.models import Location
from app.schemas.location import SLocationOut, SLocationCreate
from app.services.business.base import BaseBusinessService
from app.services.location import LocationService


class LocationBusinessService(BaseBusinessService):
    location_service: LocationService

    @new_session(readonly=True)
    async def get_all(self) -> list[SLocationOut]:
        locations: List[Location] = await self.location_service.get_all()
        return [SLocationOut(**location.model_dump()) for location in locations]

    @new_session(readonly=True)
    async def get_by_id(self, location_id: int) -> SLocationOut:
        location: Location = await self.location_service.get_one_by_id(location_id)
        return SLocationOut(**location.model_dump())

    @new_session()
    async def create_location(self, location_data: SLocationCreate) -> SLocationOut:
        location: Location = await self.location_service.create(**location_data.model_dump())
        return SLocationOut(**location.model_dump())


