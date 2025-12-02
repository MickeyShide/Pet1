from fastapi import APIRouter
from starlette import status

from app.api.deps import UserDepends
from app.schemas.payment import SPaymentOut
from app.services.business.payments import PaymentBusinessService

router = APIRouter(prefix="/payments", tags=["Payments"])


@router.post(
    path="/{payment_id}/confirm",
    response_model=SPaymentOut,
    status_code=status.HTTP_200_OK,
    summary="Confirm payment (fake)",
)
async def confirm_payment_route(payment_id: int, token_data: UserDepends):
    return await PaymentBusinessService(token_data).confirm_payment(payment_id=payment_id)
