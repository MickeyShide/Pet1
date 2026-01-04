from datetime import datetime

from fastapi import APIRouter, Query
from starlette import status

from app.api.deps import AdminDepends, TimeSlotDateRangeDepends
from app.schemas.timeslot import STimeSlotOut, STimeSlotRangeOut, STimeSlotUpdate
from app.services.business.timeslots import TimeSlotBusinessService

router = APIRouter(prefix="/timeslots", tags=["TimeSlots"])


@router.get(
    path="",
    response_model=list[STimeSlotRangeOut],
    status_code=status.HTTP_200_OK,
    description="Return timeslots by room and date range",
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
    description="Update timeslot by id", )
async def update_timeslot_by_id(
        timeslot_id: int, timeslot_data: STimeSlotUpdate, admin_data: AdminDepends
) -> STimeSlotOut:
    return await TimeSlotBusinessService().update_timeslot_by_id(
        timeslot_id=timeslot_id, timeslot_data=timeslot_data
    )


@router.delete(
    path='/{timeslot_id}',
    status_code=status.HTTP_204_NO_CONTENT,
    description="Delete timeslot by id", )
async def delete_timeslot_by_id(timeslot_id: int, admin_data: AdminDepends) -> None:
    return await TimeSlotBusinessService().delete_timeslot_by_id(timeslot_id=timeslot_id)
