from typing import List

from fastapi import APIRouter, Query, Depends
from starlette import status

from app.api.deps import UserDepends
from app.schemas.booking import SBookingOut, SBookingCreate, SBookingOutAfterCreate, SBookingOutWithTimeslots, \
    SBookingFilters
from app.services.business.bookings import BookingsBusinessService

router = APIRouter(prefix="/bookings", tags=["Bookings"])


@router.post(
    path="/",
    status_code=status.HTTP_201_CREATED,
    response_model=SBookingOutAfterCreate,
    description="Create a new booking",
)
async def create_booking_route(
        booking_data: SBookingCreate,
        token_data: UserDepends
) -> SBookingOutAfterCreate:
    return await BookingsBusinessService(token_data=token_data).create_booking(booking_data)

@router.get(
    path="/",
    status_code=status.HTTP_200_OK,
    response_model=List[SBookingOutWithTimeslots],
    description="Get all user bookings with optional filters", )
async def get_all_user_bookings(token_data: UserDepends, booking_filters: SBookingFilters | None = Depends()) -> List[SBookingOutWithTimeslots]:
    return await BookingsBusinessService(token_data).get_my_bookings(booking_filters)