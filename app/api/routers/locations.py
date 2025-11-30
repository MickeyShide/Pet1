from typing import List

from fastapi import APIRouter
from starlette import status

from app.api.deps import UserDepends
from app.schemas.location import SLocationOut, SLocationCreate
from app.services.business.locations import LocationBusinessService

router = APIRouter(prefix="/locations", tags=["Locations"])


@router.get(
    path='/',
    response_model=List[SLocationOut],
    status_code=status.HTTP_200_OK,
    description="Return all locations", )
async def get_all_locations_route() -> List[SLocationOut]:
    return await LocationBusinessService().get_all()


@router.get(
    path='/{location_id}',
    response_model=SLocationOut,
    status_code=status.HTTP_200_OK,
    description="Return location by id", )
async def get_all_locations_route(location_id: int) -> SLocationOut:
    return await LocationBusinessService().get_by_id(location_id=location_id)


@router.post(
    path='/',
    response_model=SLocationOut,
    status_code=status.HTTP_200_OK,
    description="Create new location", )
async def create_location_route(location_data: SLocationCreate, token_data: UserDepends) -> SLocationOut:
    return await LocationBusinessService(token_data=token_data, admin_required=True).create_location(location_data)
