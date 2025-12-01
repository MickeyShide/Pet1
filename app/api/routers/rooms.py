from typing import List

from fastapi import APIRouter
from starlette import status

from app.api.deps import AdminDepends
from app.schemas.room import SRoomOut, SRoomUpdate
from app.schemas.timeslot import STimeSlotOut, STimeSlotDateRange, STimeSlotOutWithBookingStatus, STimeSlotCreate
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


@router.get(
    path='/{room_id}/timeslots',
    response_model=List[STimeSlotOutWithBookingStatus],
    status_code=status.HTTP_200_OK,
    description="Return room timeslots by date range", )
async def get_room_timeslots_route(room_id: int, date_range: STimeSlotDateRange) -> List[STimeSlotOutWithBookingStatus]:
    return await RoomBusinessService().get_timeslots_by_date_range_with_booking_flag(room_id, date_range)


@router.post(
    path='/{room_id}/timeslots',
    response_model=STimeSlotOut,
    status_code=status.HTTP_201_CREATED,
    description="Create new room timeslot", )
async def create_room_timeslot(room_id: int, timeslot_data: STimeSlotCreate, admin_data: AdminDepends) -> STimeSlotOut:
    return await RoomBusinessService().create_timeslot(room_id, timeslot_data)
