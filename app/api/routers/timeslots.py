from fastapi import APIRouter
from starlette import status

from app.api.deps import AdminDepends
from app.schemas.timeslot import STimeSlotOut, STimeSlotUpdate
from app.services.business.timeslots import TimeSlotBusinessService

router = APIRouter(prefix="/timeslots", tags=["TimeSlots"])


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
