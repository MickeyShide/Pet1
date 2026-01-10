from typing import List

from fastapi import APIRouter, Query, Body
from starlette import status

from app.api import docs
from app.api.deps import AdminDepends, TimeSlotDateRangeDepends
from app.schemas.image import SImageUploadIn, SImagePresignOut
from app.schemas.room import SRoomOut, SRoomUpdate, SRoomOutWithLocation, SRoomFilter
from app.schemas.timeslot import STimeSlotOut, STimeSlotOutWithBookingStatus, STimeSlotCreate, \
    SPriceQuoteOut, SPriceQuoteIn
from app.services.business.images import ImageBusinessService
from app.services.business.rooms import RoomBusinessService

router = APIRouter(prefix="/rooms", tags=["Rooms"])


# TODO add pagination
@router.get(
    path='',
    response_model=list[SRoomOutWithLocation],
    status_code=status.HTTP_200_OK,
    description="Return all rooms",
    responses={
        status.HTTP_200_OK: docs.response_with_example(
            "Rooms",
            [docs.ROOM_WITH_LOCATION_EXAMPLE],
            model=list[SRoomOutWithLocation],
        ),
    },
)
async def get_all_rooms_route(
        page: int = Query(default=0),
        limit: int = Query(default=5),
        filters: SRoomFilter = Body()
) -> list[SRoomOutWithLocation]:
    return await RoomBusinessService().get_all_with_location(filters, page, limit)


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
async def get_room_timeslots_route(
        room_id: int,
        date_range: TimeSlotDateRangeDepends,
) -> List[STimeSlotOutWithBookingStatus]:
    return await RoomBusinessService().get_timeslots_by_date_range_with_booking_flag(room_id, date_range)


@router.post(
    path='/{room_id}/timeslots',
    response_model=STimeSlotOut,
    status_code=status.HTTP_201_CREATED,
    description="Create new room timeslot", )
async def create_room_timeslot(room_id: int, timeslot_data: STimeSlotCreate, admin_data: AdminDepends) -> STimeSlotOut:
    return await RoomBusinessService().create_timeslot(room_id, timeslot_data)


@router.post(
    path='/{room_id}/price-quote',
    response_model=SPriceQuoteOut,
    status_code=status.HTTP_200_OK,
    description="Return room price quote for a date range", )
async def get_price_quote_route(room_id: int, data: SPriceQuoteIn) -> SPriceQuoteOut:
    return await RoomBusinessService().get_price_quote(room_id=room_id, date_from=data.date_from, date_to=data.date_to)


@router.post(
    path='/{room_id}/upload_image',
    response_model=SImagePresignOut,
    status_code=status.HTTP_200_OK,
    description="Upload image for room via presigned URL",
)
async def upload_room_image(
        room_id: int,
        payload: SImageUploadIn,
        token_data: AdminDepends,
) -> SImagePresignOut:
    return await ImageBusinessService(token_data=token_data).upload_room_image(room_id, payload)
