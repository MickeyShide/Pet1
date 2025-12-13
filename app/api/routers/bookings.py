from typing import List

from fastapi import APIRouter, Depends
from starlette import status

from app.api.deps import UserDepends
from app.models.booking import BookingStatus
from app.schemas.booking import SBookingCreate, SBookingOutAfterCreate, SBookingOutWithTimeslots, \
    SBookingFilters
from app.schemas.payment import SPaymentOut
from app.schemas.timeslot import STimeSlotFilters
from app.services.business.bookings import BookingsBusinessService
from app.services.business.payments import PaymentBusinessService

router = APIRouter(prefix="/bookings", tags=["Bookings"])


@router.post(
    path="",
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
    path="",
    status_code=status.HTTP_200_OK,
    response_model=List[SBookingOutWithTimeslots],
    description="Get all user bookings with optional filters", )
async def get_all_user_bookings(
        token_data: UserDepends,
        room_id: int | None = None,
        status: BookingStatus | None = None,
        timeslot_filters: STimeSlotFilters = Depends()
) -> List[SBookingOutWithTimeslots]:
    booking_filters = SBookingFilters(
        room_id=room_id,
        status=status,
    )
    return await BookingsBusinessService(token_data).get_my_bookings(
        booking_filters=booking_filters,
        timeslot_filters=timeslot_filters,
    )


@router.get(
    path="/{booking_id}",
    status_code=status.HTTP_200_OK,
    response_model=SBookingOutWithTimeslots,
    description="Get booking by ID", )
async def get_booking_by_id_route(
        token_data: UserDepends,
        booking_id: int,
) -> SBookingOutWithTimeslots:
    return await BookingsBusinessService(token_data).get_booking_by_id(booking_id)


@router.post(
    path="/{booking_id}/cancel",
    status_code=status.HTTP_200_OK,
    response_model=bool,
    description="Cancel booking", )
async def cancel_booking(
        token_data: UserDepends,
        booking_id: int
) -> bool:
    return await BookingsBusinessService(token_data).cancel_booking(booking_id)


@router.post(
    path="/{booking_id}/payments",
    status_code=status.HTTP_200_OK,
    response_model=SPaymentOut,
    description="Payments booking", )
async def create_payment_route(
        token_data: UserDepends,
        booking_id: int,
) -> SPaymentOut:
    return await PaymentBusinessService(token_data).create_payment(booking_id)
