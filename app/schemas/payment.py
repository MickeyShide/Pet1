from app.models.payment import PaymentStatus
from app.schemas import BaseSchema


class SPaymentBase(BaseSchema):
    booking_id: int
    external_id: str
    status: PaymentStatus


class SPaymentOut(SPaymentBase):
    id: int


class SPaymentCreate(BaseSchema):
    booking_id: int
    external_id: str
