from typing import List

from fastapi import APIRouter
from starlette import status

from app.api.deps import AdminDepends
from app.schemas.location import SLocationOut, SLocationCreate, SLocationUpdate
from app.schemas.room import SRoomOut, SRoomCreate
from app.services.business.locations import LocationBusinessService
from app.services.business.rooms import RoomBusinessService

router = APIRouter(prefix="/locations", tags=["Locations"])


@router.get(
    path='',
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
async def get_location_by_id_route(location_id: int) -> SLocationOut:
    return await LocationBusinessService().get_by_id(location_id=location_id)


@router.post(
    path='',
    response_model=SLocationOut,
    status_code=status.HTTP_200_OK,
    description="Create new location", )
async def create_location_route(location_data: SLocationCreate, token_data: AdminDepends) -> SLocationOut:
    return await LocationBusinessService().create_location(location_data)


@router.patch(
    path='/{location_id}',
    response_model=SLocationOut,
    status_code=status.HTTP_200_OK,
    description="Update existing location", )
async def update_location_route(location_id: int, location_data: SLocationUpdate,
                                token_data: AdminDepends) -> SLocationOut:
    return await LocationBusinessService().update_by_id(location_id, location_data)


@router.delete(
    path='/{location_id}',
    status_code=status.HTTP_204_NO_CONTENT,
    description="Delete existing location", )
async def delete_location_route(location_id: int, token_data: AdminDepends) -> None:
    return await LocationBusinessService().delete_by_id(location_id)


@router.get(
    path="/{location_id}/rooms",
    response_model=List[SRoomOut],
    status_code=status.HTTP_200_OK,
    description="Return all rooms by location id",
)
async def get_all_rooms_by_location_id_route(location_id: int) -> List[SRoomOut]:
    return await LocationBusinessService().get_rooms_by_location_id(location_id=location_id)


@router.post(
    path="/{location_id}/rooms",
    response_model=SRoomOut,
    status_code=status.HTTP_200_OK,
    description="Create new room",
)
async def create_room_route(location_id: int, room_data: SRoomCreate, token_data: AdminDepends) -> SRoomOut:
    return await RoomBusinessService().create_by_location_id(location_id, room_data)
