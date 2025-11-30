from fastapi import APIRouter
from starlette import status

from app.api.deps import AdminDepends
from app.schemas.room import SRoomOut, SRoomUpdate
from app.services.business.locations import LocationBusinessService
from app.services.business.rooms import RoomBusinessService

router = APIRouter(prefix="/rooms", tags=["Rooms"])


@router.get(
    path='/{room_id}',
    response_model=SRoomOut,
    status_code=status.HTTP_200_OK,
    description="Return room by id", )
async def get_room_by_id_route(room_id: int) -> SRoomOut:
    return await RoomBusinessService().get_by_id(room_id=room_id)


@router.patch(
    path='/{room_id}',
    response_model=SRoomOut,
    status_code=status.HTTP_200_OK,
    description="Update existing room", )
async def update_room_route(room_id: int, room_data: SRoomUpdate, token_data: AdminDepends) -> SRoomOut:
    return await RoomBusinessService().update_by_id(room_id, room_data)


@router.delete(
    path='/{room_id}',
    status_code=status.HTTP_204_NO_CONTENT,
    description="Delete existing room", )
async def delete_room_route(room_id: int, token_data: AdminDepends) -> None:
    return await RoomBusinessService().delete_by_id(room_id)
