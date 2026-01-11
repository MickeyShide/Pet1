from fastapi import APIRouter
from starlette import status

from app.api import docs
from app.api.deps import UserDepends
from app.schemas.payment import SPaymentOut
from app.services.business.payments import PaymentBusinessService

router = APIRouter(prefix="/payments", tags=["Payments"])


@router.post(
    path="/{payment_id}/confirm",
    response_model=SPaymentOut,
    status_code=status.HTTP_200_OK,
    summary="Confirm payment (fake)",
    responses={
        status.HTTP_200_OK: docs.response_with_example(
            "Payment confirmed",
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
                "payment_not_found": docs.example(
                    "Payment not found",
                    {"detail": "Payment not found"},
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
            },
        ),
    },
)
async def confirm_payment_route(payment_id: int, token_data: UserDepends):
    return await PaymentBusinessService(token_data).confirm_payment(payment_id=payment_id)
