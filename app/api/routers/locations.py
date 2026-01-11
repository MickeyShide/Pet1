from typing import List

from fastapi import APIRouter
from starlette import status

from app.api import docs
from app.api.deps import AdminDepends
from app.schemas.image import SImageUploadIn, SImagePresignOut
from app.schemas.location import SLocationOut, SLocationCreate, SLocationUpdate
from app.schemas.room import SRoomOut, SRoomCreate
from app.services.business.images import ImageBusinessService
from app.services.business.locations import LocationBusinessService
from app.services.business.rooms import RoomBusinessService

router = APIRouter(prefix="/locations", tags=["Locations"])


@router.get(
    path='',
    response_model=List[SLocationOut],
    status_code=status.HTTP_200_OK,
    description="Return all locations",
    responses={
        status.HTTP_200_OK: docs.response_with_example(
            "Locations",
            [docs.LOCATION_EXAMPLE],
            model=List[SLocationOut],
        ),
    },
)
async def get_all_locations_route() -> List[SLocationOut]:
    return await LocationBusinessService().get_all()


@router.get(
    path='/{location_id}',
    response_model=SLocationOut,
    status_code=status.HTTP_200_OK,
    description="Return location by id",
    responses={
        status.HTTP_200_OK: docs.response_with_example(
            "Location",
            docs.LOCATION_EXAMPLE,
            model=SLocationOut,
        ),
        status.HTTP_404_NOT_FOUND: docs.error_response(
            "Not Found",
            {
                "location_not_found": docs.example(
                    "Location not found",
                    {"detail": "no_item_in_<class 'app.models.location.Location'>_with_1_id"},
                )
            },
        ),
    },
)
async def get_location_by_id_route(location_id: int) -> SLocationOut:
    return await LocationBusinessService().get_by_id(location_id=location_id)


@router.post(
    path='',
    response_model=SLocationOut,
    status_code=status.HTTP_200_OK,
    description="Create new location",
    responses={
        status.HTTP_200_OK: docs.response_with_example(
            "Location created",
            docs.LOCATION_EXAMPLE,
            model=SLocationOut,
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
async def create_location_route(location_data: SLocationCreate, token_data: AdminDepends) -> SLocationOut:
    return await LocationBusinessService().create_location(location_data)


@router.patch(
    path='/{location_id}',
    response_model=SLocationOut,
    status_code=status.HTTP_200_OK,
    description="Update existing location",
    responses={
        status.HTTP_200_OK: docs.response_with_example(
            "Location updated",
            docs.LOCATION_EXAMPLE,
            model=SLocationOut,
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
                "location_not_found": docs.example(
                    "Location not found",
                    {"detail": "no_item_in_<class 'app.models.location.Location'>_with_1_id"},
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
async def update_location_route(location_id: int, location_data: SLocationUpdate,
                                token_data: AdminDepends) -> SLocationOut:
    return await LocationBusinessService().update_by_id(location_id, location_data)


@router.delete(
    path='/{location_id}',
    status_code=status.HTTP_204_NO_CONTENT,
    description="Delete existing location",
    responses={
        status.HTTP_204_NO_CONTENT: {
            "description": "Location deleted",
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
                "location_not_found": docs.example(
                    "Location not found",
                    {"detail": "no_item_in_<class 'app.models.location.Location'>_with_1_id"},
                )
            },
        ),
    },
)
async def delete_location_route(location_id: int, token_data: AdminDepends) -> None:
    return await LocationBusinessService().delete_by_id(location_id)


@router.get(
    path="/{location_id}/rooms",
    response_model=List[SRoomOut],
    status_code=status.HTTP_200_OK,
    description="Return all rooms by location id",
    responses={
        status.HTTP_200_OK: docs.response_with_example(
            "Location rooms",
            [docs.ROOM_EXAMPLE],
            model=List[SRoomOut],
        ),
        status.HTTP_404_NOT_FOUND: docs.error_response(
            "Not Found",
            {
                "location_not_found": docs.example(
                    "Location not found",
                    {"detail": "no_item_in_<class 'app.models.location.Location'>_with_1_id"},
                )
            },
        ),
    },
)
async def get_all_rooms_by_location_id_route(location_id: int) -> List[SRoomOut]:
    return await LocationBusinessService().get_rooms_by_location_id(location_id=location_id)


@router.post(
    path="/{location_id}/rooms",
    response_model=SRoomOut,
    status_code=status.HTTP_200_OK,
    description="Create new room",
    responses={
        status.HTTP_200_OK: docs.response_with_example(
            "Room created",
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
                "location_not_found": docs.example(
                    "Location not found",
                    {"detail": "no_item_in_<class 'app.models.location.Location'>_with_1_id"},
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
async def create_room_route(location_id: int, room_data: SRoomCreate, token_data: AdminDepends) -> SRoomOut:
    return await RoomBusinessService().create_by_location_id(location_id, room_data)


@router.post(
    path="/{location_id}/upload_image",
    response_model=SImagePresignOut,
    status_code=status.HTTP_200_OK,
    description="Upload image for location via presigned URL",
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
                "location_not_found": docs.example(
                    "Location not found",
                    {"detail": "no_item_in_<class 'app.models.location.Location'>_with_1_id"},
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
async def upload_location_image(
        location_id: int,
        payload: SImageUploadIn,
        token_data: AdminDepends,
) -> SImagePresignOut:
    return await ImageBusinessService(token_data=token_data).upload_location_image(location_id, payload)
