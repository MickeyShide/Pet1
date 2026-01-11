from fastapi import APIRouter, Query
from starlette import status

from app.api import docs
from app.api.deps import AdminDepends, TimeSlotDateRangeDepends
from app.schemas.timeslot import STimeSlotOut, STimeSlotRangeOut, STimeSlotUpdate
from app.services.business.timeslots import TimeSlotBusinessService

router = APIRouter(prefix="/timeslots", tags=["TimeSlots"])


@router.get(
    path="",
    response_model=list[STimeSlotRangeOut],
    status_code=status.HTTP_200_OK,
    description="Return timeslots by room and date range",
    responses={
        status.HTTP_200_OK: docs.response_with_example(
            "Timeslots",
            [docs.TIMESLOT_RANGE_EXAMPLE],
            model=list[STimeSlotRangeOut],
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
async def get_timeslots_route(
        date_range: TimeSlotDateRangeDepends,
        room_id: int = Query(...),
) -> list[STimeSlotRangeOut]:
    return await TimeSlotBusinessService().get_by_room_and_date_range(
        room_id=room_id,
        date_from=date_range.date_from,
        date_to=date_range.date_to,
    )


@router.patch(
    path='/{timeslot_id}',
    response_model=STimeSlotOut,
    status_code=status.HTTP_200_OK,
    description="Update timeslot by id",
    responses={
        status.HTTP_200_OK: docs.response_with_example(
            "Timeslot updated",
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
                "timeslot_not_found": docs.example(
                    "Timeslot not found",
                    {"detail": "no_item_in_<class 'app.models.timeslot.TimeSlot'>_with_1_id"},
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
async def update_timeslot_by_id(
        timeslot_id: int, timeslot_data: STimeSlotUpdate, admin_data: AdminDepends
) -> STimeSlotOut:
    return await TimeSlotBusinessService().update_timeslot_by_id(
        timeslot_id=timeslot_id, timeslot_data=timeslot_data
    )


@router.delete(
    path='/{timeslot_id}',
    status_code=status.HTTP_204_NO_CONTENT,
    description="Delete timeslot by id",
    responses={
        status.HTTP_204_NO_CONTENT: {
            "description": "Timeslot deleted",
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
                "timeslot_not_found": docs.example(
                    "Timeslot not found",
                    {"detail": "no_item_in_<class 'app.models.timeslot.TimeSlot'>_with_1_id"},
                )
            },
        ),
    },
)
async def delete_timeslot_by_id(timeslot_id: int, admin_data: AdminDepends) -> None:
    return await TimeSlotBusinessService().delete_timeslot_by_id(timeslot_id=timeslot_id)
