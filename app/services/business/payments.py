from faker import Faker

from app.db.base import new_session
from app.models import Payment, Booking
from app.models.payment import PaymentStatus
from app.schemas.payment import SPaymentCreate, SPaymentOut
from app.services.booking import BookingService
from app.services.business.base import BaseBusinessService
from app.services.payment import PaymentService
from app.utils.err.base.not_found import NotFoundException
from app.utils.err.booking import BookingNotFound
from app.utils.err.payment import PaymentNotFound


class PaymentBusinessService(BaseBusinessService):
    payment_service: PaymentService
    booking_service: BookingService

    @new_session()
    async def create_payment(self, booking_id: int) -> SPaymentOut:

        booking = await self.booking_service.get_one_by_id(booking_id)

        if not self.admin and booking.user_id != self.user_id:
            raise BookingNotFound()

        payment: Payment = await self.payment_service.create(
            **SPaymentCreate(
                booking_id=booking_id,
                external_id=Faker().uuid4(),
            ).model_dump()
        )

        return SPaymentOut.from_model(payment)

    @new_session()
    async def confirm_payment(self, payment_id: int) -> SPaymentOut:
        try:
            payment: Payment = await self.payment_service.get_one_by_id(payment_id)
            booking: Booking = await self.booking_service.get_one_by_id(payment.booking_id)
            if not self.admin and booking.user_id != self.user_id:
                raise PaymentNotFound()
        except NotFoundException:
            raise PaymentNotFound()

        updated_payment: Payment = await self.payment_service.update_by_id(payment_id, status=PaymentStatus.SUCCESS)
        updated_booking: Booking = await self.booking_service.set_booking_paid(updated_payment.booking_id)

        return SPaymentOut.from_model(payment)
