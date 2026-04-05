from typing import Annotated, List
from uuid import UUID

from fastapi import APIRouter, Header
from starlette import status

from app.api import docs
from app.api.deps import BookingFiltersDepends, TimeSlotFiltersDepends, UserDepends
from app.schemas.booking import (
    SBookingCreate,
    SBookingCreateFlexible,
    SBookingOutAfterCreate,
    SBookingOutWithTimeslots,
)
from app.schemas.payment import SPaymentOut
from app.services.business.bookings import BookingsBusinessService
from app.services.business.payments import PaymentBusinessService

router = APIRouter(prefix="/bookings", tags=["Bookings"])
IdempotencyKeyHeader = Annotated[UUID | None, Header(alias="Idempotency-Key")]


@router.post(
    path="",
    status_code=status.HTTP_201_CREATED,
    response_model=SBookingOutAfterCreate,
    description="Create a new booking",
    responses={
        status.HTTP_201_CREATED: docs.response_with_example(
            "Booking created",
            docs.BOOKING_OUT_AFTER_CREATE_EXAMPLE,
            model=SBookingOutAfterCreate,
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
        status.HTTP_404_NOT_FOUND: docs.error_response(
            "Not Found",
            {
                "timeslot_not_found": docs.example(
                    "Timeslot not found",
                    {"detail": "Timeslot not found"},
                )
            },
        ),
        status.HTTP_409_CONFLICT: docs.error_response(
            "Conflict",
            {
                "timeslot_taken": docs.example(
                    "Timeslot already taken",
                    {"detail": "Timeslot already taken"},
                ),
                "timeslot_blocked": docs.example(
                    "Timeslot is blocked",
                    {"detail": "Timeslot is blocked"},
                ),
                "timeslot_cancelled": docs.example(
                    "Timeslot is cancelled",
                    {"detail": "Timeslot is cancelled"},
                ),
                "idempotency_payload_conflict": docs.example(
                    "Idempotency payload mismatch",
                    {"detail": "Idempotency key is already used with another payload"},
                ),
                "idempotency_in_progress": docs.example(
                    "Idempotency in progress",
                    {"detail": "Booking request with this idempotency key is still in progress"},
                ),
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
async def create_booking_route(
        booking_data: SBookingCreate,
        token_data: UserDepends,
        idempotency_key: IdempotencyKeyHeader = None,
) -> SBookingOutAfterCreate:
    return await BookingsBusinessService(token_data=token_data).create_booking(
        booking_data,
        idempotency_key=idempotency_key,
    )


@router.post(
    path="/flexible",
    status_code=status.HTTP_201_CREATED,
    response_model=SBookingOutWithTimeslots,
    description="Create a new booking",
    responses={
        status.HTTP_201_CREATED: docs.response_with_example(
            "Booking created",
            docs.BOOKING_WITH_TIMESLOT_EXAMPLE,
            model=SBookingOutWithTimeslots,
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
        status.HTTP_404_NOT_FOUND: docs.error_response(
            "Not Found",
            {
                "room_not_found": docs.example(
                    "Room not found",
                    {"detail": "Room not found"},
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
                "invalid_timeslot": docs.example(
                    "Timeslot can not be created",
                    {"detail": "Timeslot can not be created"},
                ),
                "timeslot_taken": docs.example(
                    "Timeslot already taken",
                    {"detail": "Timeslot already taken"},
                ),
                "timeslot_blocked": docs.example(
                    "Timeslot is blocked",
                    {"detail": "Timeslot is blocked"},
                ),
                "timeslot_cancelled": docs.example(
                    "Timeslot is cancelled",
                    {"detail": "Timeslot is cancelled"},
                ),
                "idempotency_payload_conflict": docs.example(
                    "Idempotency payload mismatch",
                    {"detail": "Idempotency key is already used with another payload"},
                ),
                "idempotency_in_progress": docs.example(
                    "Idempotency in progress",
                    {"detail": "Booking request with this idempotency key is still in progress"},
                ),
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
async def create_booking_flexible_route(
        booking_data: SBookingCreateFlexible,
        token_data: UserDepends,
        idempotency_key: IdempotencyKeyHeader = None,
) -> SBookingOutWithTimeslots:
    return await BookingsBusinessService(token_data=token_data).create_booking_flexible(
        booking_data,
        idempotency_key=idempotency_key,
    )


@router.get(
    path="",
    status_code=status.HTTP_200_OK,
    response_model=List[SBookingOutWithTimeslots],
    description="Get all user bookings with optional filters",
    responses={
        status.HTTP_200_OK: docs.response_with_example(
            "User bookings",
            [docs.BOOKING_WITH_TIMESLOT_EXAMPLE],
            model=List[SBookingOutWithTimeslots],
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
    },
)
async def get_all_user_bookings(
        token_data: UserDepends,
        booking_filters: BookingFiltersDepends,
        timeslot_filters: TimeSlotFiltersDepends
) -> List[SBookingOutWithTimeslots]:
    return await BookingsBusinessService(token_data).get_my_bookings(
        booking_filters=booking_filters,
        timeslot_filters=timeslot_filters,
    )


@router.get(
    path="/{booking_id}",
    status_code=status.HTTP_200_OK,
    response_model=SBookingOutWithTimeslots,
    description="Get booking by ID",
    responses={
        status.HTTP_200_OK: docs.response_with_example(
            "Booking details",
            docs.BOOKING_WITH_TIMESLOT_EXAMPLE,
            model=SBookingOutWithTimeslots,
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
        status.HTTP_404_NOT_FOUND: docs.error_response(
            "Not Found",
            {
                "booking_not_found": docs.example(
                    "Booking not found",
                    {"detail": "Booking with id 123 not found"},
                )
            },
        ),
    },
)
async def get_booking_by_id_route(
        token_data: UserDepends,
        booking_id: int,
) -> SBookingOutWithTimeslots:
    return await BookingsBusinessService(token_data).get_booking_by_id(booking_id)


@router.post(
    path="/{booking_id}/cancel",
    status_code=status.HTTP_200_OK,
    response_model=bool,
    description="Cancel booking",
    responses={
        status.HTTP_200_OK: docs.response_with_example(
            "Booking canceled",
            True,
            model=bool,
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
        status.HTTP_404_NOT_FOUND: docs.error_response(
            "Not Found",
            {
                "booking_not_found": docs.example(
                    "Booking not found",
                    {"detail": "Booking with id 123 not found"},
                )
            },
        ),
        status.HTTP_409_CONFLICT: docs.error_response(
            "Conflict",
            {
                "invalid_status": docs.example(
                    "Booking status invalid",
                    {"detail": "Booking with id 123 status: PAID"},
                )
            },
        ),
    },
)
async def cancel_booking(
        token_data: UserDepends,
        booking_id: int
) -> bool:
    return await BookingsBusinessService(token_data).cancel_booking(booking_id)


@router.post(
    path="/{booking_id}/payments",
    status_code=status.HTTP_200_OK,
    response_model=SPaymentOut,
    description="Payments booking",
    responses={
        status.HTTP_200_OK: docs.response_with_example(
            "Payment created",
            docs.PAYMENT_EXAMPLE,
            model=SPaymentOut,
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
        status.HTTP_404_NOT_FOUND: docs.error_response(
            "Not Found",
            {
                "booking_not_found": docs.example(
                    "Booking not found",
                    {"detail": "Booking not found"},
                )
            },
        ),
        status.HTTP_409_CONFLICT: docs.error_response(
            "Conflict",
            {
                "booking_not_payable": docs.example(
                    "Booking cannot be paid",
                    {"detail": "Booking cannot be paid"},
                ),
                "payment_exists": docs.example(
                    "Payment already exists",
                    {"detail": "Payment already exists"},
                ),
                "provider_rejected": docs.example(
                    "Provider rejected",
                    {"detail": "card declined"},
                ),
            },
        ),
        status.HTTP_503_SERVICE_UNAVAILABLE: docs.error_response(
            "Service Unavailable",
            {
                "provider_unavailable": docs.example(
                    "Provider unavailable",
                    {"detail": "Payment provider is unavailable for create_payment"},
                )
            },
        ),
    },
)
async def create_payment_route(
        token_data: UserDepends,
        booking_id: int,
) -> SPaymentOut:
    return await PaymentBusinessService(token_data).create_payment(booking_id)
