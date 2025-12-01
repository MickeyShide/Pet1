from fastapi import APIRouter
from starlette import status

from app.api.deps import UserDepends
from app.schemas.booking import SBookingOut, SBookingCreate
from app.services.business.bookings import BookingsBusinessService

router = APIRouter(prefix="/bookings", tags=["Bookings"])


@router.post(
    path="/",
    status_code=status.HTTP_201_CREATED,
    response_model=SBookingOut,
    description="Create a new booking",
)
async def create_booking_route(
        booking_data: SBookingCreate,
        token_data: UserDepends
) -> SBookingOut:
    return await BookingsBusinessService(token_data=token_data).create_booking(booking_data)
