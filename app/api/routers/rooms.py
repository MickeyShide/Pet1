from typing import List

from fastapi import APIRouter, Query, Depends
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
        filters: SRoomFilter | None = None,
        page: int = Query(default=0),
        limit: int = Query(default=5),
) -> list[SRoomOutWithLocation]:
    if filters is None:
        filters = SRoomFilter()
    return await RoomBusinessService().get_all_with_location(filters, page, limit)


@router.get(
    path='/{room_id}',
    response_model=SRoomOut,
    status_code=status.HTTP_200_OK,
    description="Return room by id",
    responses={
        status.HTTP_200_OK: docs.response_with_example(
            "Room",
            docs.ROOM_EXAMPLE,
            model=SRoomOut,
        ),
        status.HTTP_404_NOT_FOUND: docs.error_response(
            "Not Found",
            {
                "room_not_found": docs.example(
                    "Room not found",
                    {"detail": "no_item_in_<class 'app.models.room.Room'>_with_1_id"},
                )
            },
        ),
    },
)
async def get_room_by_id_route(room_id: int) -> SRoomOut:
    return await RoomBusinessService().get_by_id(room_id=room_id)


@router.patch(
    path='/{room_id}',
    response_model=SRoomOut,
    status_code=status.HTTP_200_OK,
    description="Update existing room",
    responses={
        status.HTTP_200_OK: docs.response_with_example(
            "Room updated",
            docs.ROOM_EXAMPLE,
            model=SRoomOut,
        ),
        status.HTTP_401_UNAUTHORIZED: docs.error_response(
            "Unauthorized",
            {
                "missing_access_token": docs.example(
                    "Missing access token",
                    {"detail": "Missing access token"},
                ),
                "invalid_access_token": docs.example(
                    "Invalid access token",
                    {"detail": "Invalid access token"},
                ),
            },
        ),
        status.HTTP_403_FORBIDDEN: docs.error_response(
            "Forbidden",
            {
                "not_allowed": docs.example(
                    "Not allowed",
                    {"detail": "Not allowed"},
                )
            },
        ),
        status.HTTP_404_NOT_FOUND: docs.error_response(
            "Not Found",
            {
                "room_not_found": docs.example(
                    "Room not found",
                    {"detail": "no_item_in_<class 'app.models.room.Room'>_with_1_id"},
                )
            },
        ),
        status.HTTP_422_UNPROCESSABLE_ENTITY: docs.error_response(
            "Validation Error",
            {
                "invalid_payload": docs.example(
                    "Validation error",
                    docs.validation_error_example(
                        "At least one field must be provided",
                        ["body"],
                        {},
                    ),
                )
            },
        ),
    },
)
async def update_room_route(room_id: int, room_data: SRoomUpdate, token_data: AdminDepends) -> SRoomOut:
    return await RoomBusinessService().update_by_id(room_id, room_data)


@router.delete(
    path='/{room_id}',
    status_code=status.HTTP_204_NO_CONTENT,
    description="Delete existing room",
    responses={
        status.HTTP_204_NO_CONTENT: {
            "description": "Room deleted",
        },
        status.HTTP_401_UNAUTHORIZED: docs.error_response(
            "Unauthorized",
            {
                "missing_access_token": docs.example(
                    "Missing access token",
                    {"detail": "Missing access token"},
                ),
                "invalid_access_token": docs.example(
                    "Invalid access token",
                    {"detail": "Invalid access token"},
                ),
            },
        ),
        status.HTTP_403_FORBIDDEN: docs.error_response(
            "Forbidden",
            {
                "not_allowed": docs.example(
                    "Not allowed",
                    {"detail": "Not allowed"},
                )
            },
        ),
        status.HTTP_404_NOT_FOUND: docs.error_response(
            "Not Found",
            {
                "room_not_found": docs.example(
                    "Room not found",
                    {"detail": "no_item_in_<class 'app.models.room.Room'>_with_1_id"},
                )
            },
        ),
    },
)
async def delete_room_route(room_id: int, token_data: AdminDepends) -> None:
    return await RoomBusinessService().delete_by_id(room_id)


@router.get(
    path='/{room_id}/timeslots',
    response_model=List[STimeSlotOutWithBookingStatus],
    status_code=status.HTTP_200_OK,
    description="Return room timeslots by date range",
    responses={
        status.HTTP_200_OK: docs.response_with_example(
            "Room timeslots",
            [docs.TIMESLOT_WITH_BOOKING_STATUS_EXAMPLE],
            model=List[STimeSlotOutWithBookingStatus],
        ),
        status.HTTP_404_NOT_FOUND: docs.error_response(
            "Not Found",
            {
                "room_not_found": docs.example(
                    "Room not found",
                    {"detail": "no_item_in_<class 'app.models.room.Room'>_with_1_id"},
                )
            },
        ),
        status.HTTP_422_UNPROCESSABLE_ENTITY: docs.error_response(
            "Validation Error",
            {
                "invalid_query": docs.example(
                    "Validation error",
                    docs.VALIDATION_ERROR_EXAMPLE,
                )
            },
        ),
    },
)
async def get_room_timeslots_route(
        room_id: int,
        date_range: TimeSlotDateRangeDepends,
) -> List[STimeSlotOutWithBookingStatus]:
    return await RoomBusinessService().get_timeslots_by_date_range_with_booking_flag(room_id, date_range)


@router.post(
    path='/{room_id}/timeslots',
    response_model=STimeSlotOut,
    status_code=status.HTTP_201_CREATED,
    description="Create new room timeslot",
    responses={
        status.HTTP_201_CREATED: docs.response_with_example(
            "Timeslot created",
            docs.TIMESLOT_EXAMPLE,
            model=STimeSlotOut,
        ),
        status.HTTP_401_UNAUTHORIZED: docs.error_response(
            "Unauthorized",
            {
                "missing_access_token": docs.example(
                    "Missing access token",
                    {"detail": "Missing access token"},
                ),
                "invalid_access_token": docs.example(
                    "Invalid access token",
                    {"detail": "Invalid access token"},
                ),
            },
        ),
        status.HTTP_403_FORBIDDEN: docs.error_response(
            "Forbidden",
            {
                "not_allowed": docs.example(
                    "Not allowed",
                    {"detail": "Not allowed"},
                )
            },
        ),
        status.HTTP_404_NOT_FOUND: docs.error_response(
            "Not Found",
            {
                "room_not_found": docs.example(
                    "Room not found",
                    {"detail": "no_item_in_<class 'app.models.room.Room'>_with_1_id"},
                )
            },
        ),
        status.HTTP_422_UNPROCESSABLE_ENTITY: docs.error_response(
            "Validation Error",
            {
                "invalid_payload": docs.example(
                    "Validation error",
                    docs.VALIDATION_ERROR_EXAMPLE,
                )
            },
        ),
    },
)
async def create_room_timeslot(room_id: int, timeslot_data: STimeSlotCreate, admin_data: AdminDepends) -> STimeSlotOut:
    return await RoomBusinessService().create_timeslot(room_id, timeslot_data)


@router.post(
    path='/{room_id}/price-quote',
    response_model=SPriceQuoteOut,
    status_code=status.HTTP_200_OK,
    description="Return room price quote for a date range",
    responses={
        status.HTTP_200_OK: docs.response_with_example(
            "Price quote",
            docs.PRICE_QUOTE_EXAMPLE,
            model=SPriceQuoteOut,
        ),
        status.HTTP_404_NOT_FOUND: docs.error_response(
            "Not Found",
            {
                "room_not_found": docs.example(
                    "Room not found",
                    {"detail": "no_item_in_<class 'app.models.room.Room'>_with_1_id"},
                )
            },
        ),
        status.HTTP_409_CONFLICT: docs.error_response(
            "Conflict",
            {
                "not_flexible": docs.example(
                    "Not flexible timeslot type",
                    {"detail": "Timeslot type of this room ISNT flexible."},
                ),
                "invalid_duration": docs.example(
                    "Invalid booking duration",
                    {
                        "detail": (
                                "Duration must be >= 60 and aligned to 30 minutes."
                        )
                    },
                ),
            },
        ),
        status.HTTP_422_UNPROCESSABLE_ENTITY: docs.error_response(
            "Validation Error",
            {
                "invalid_payload": docs.example(
                    "Validation error",
                    docs.validation_error_example(
                        "date_to must be greater than date_from",
                        ["body", "date_to"],
                        "2024-05-01T09:00:00+00:00",
                    ),
                )
            },
        ),
    },
)
async def get_price_quote_route(room_id: int, data: SPriceQuoteIn) -> SPriceQuoteOut:
    return await RoomBusinessService().get_price_quote(
        room_id=room_id,
        date_from=data.date_from,
        date_to=data.date_to,
    )


@router.post(
    path='/{room_id}/upload_image',
    response_model=SImagePresignOut,
    status_code=status.HTTP_200_OK,
    description="Upload image for room via presigned URL",
    responses={
        status.HTTP_200_OK: docs.response_with_example(
            "Image presigned upload",
            docs.IMAGE_PRESIGN_EXAMPLE,
            model=SImagePresignOut,
        ),
        status.HTTP_401_UNAUTHORIZED: docs.error_response(
            "Unauthorized",
            {
                "missing_access_token": docs.example(
                    "Missing access token",
                    {"detail": "Missing access token"},
                ),
                "invalid_access_token": docs.example(
                    "Invalid access token",
                    {"detail": "Invalid access token"},
                ),
            },
        ),
        status.HTTP_403_FORBIDDEN: docs.error_response(
            "Forbidden",
            {
                "not_allowed": docs.example(
                    "Not allowed",
                    {"detail": "Not allowed"},
                )
            },
        ),
        status.HTTP_404_NOT_FOUND: docs.error_response(
            "Not Found",
            {
                "room_not_found": docs.example(
                    "Room not found",
                    {"detail": "no_item_in_<class 'app.models.room.Room'>_with_1_id"},
                )
            },
        ),
        status.HTTP_413_REQUEST_ENTITY_TOO_LARGE: docs.error_response(
            "Payload Too Large",
            {
                "payload_too_large": docs.example(
                    "Payload too large",
                    {"detail": "payload_too_large"},
                )
            },
        ),
        status.HTTP_415_UNSUPPORTED_MEDIA_TYPE: docs.error_response(
            "Unsupported Media Type",
            {
                "unsupported_media_type": docs.example(
                    "Unsupported media type",
                    {"detail": "unsupported_media_type"},
                )
            },
        ),
        status.HTTP_422_UNPROCESSABLE_ENTITY: docs.error_response(
            "Validation Error",
            {
                "invalid_filename": docs.example(
                    "Invalid filename",
                    {"detail": "invalid_filename"},
                ),
                "invalid_file_size": docs.example(
                    "Invalid file size",
                    {"detail": "invalid_file_size"},
                ),
            },
        ),
    },
)
async def upload_room_image(
        room_id: int,
        payload: SImageUploadIn,
        token_data: AdminDepends,
) -> SImagePresignOut:
    return await ImageBusinessService(token_data=token_data).upload_room_image(room_id, payload)
