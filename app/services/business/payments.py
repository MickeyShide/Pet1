from datetime import datetime, timezone

from faker import Faker

from app.db.base import new_session
from app.models import Payment, Booking
from app.models.booking import BookingStatus
from app.models.payment import PaymentStatus
from app.schemas.payment import SPaymentCreate, SPaymentOut
from app.services.booking import BookingService
from app.services.business.base import BaseBusinessService
from app.services.payment import PaymentService
from app.utils.err.base.not_found import NotFoundException
from app.utils.err.booking import BookingNotFound, BookingNotPayable
from app.utils.err.payment import PaymentNotFound, PaymentAlreadyExists


class PaymentBusinessService(BaseBusinessService):
    payment_service: PaymentService
    booking_service: BookingService

    @new_session()
    async def create_payment(self, booking_id: int) -> SPaymentOut:

        booking = await self.booking_service.get_one_by_id(booking_id)

        if not self.admin and booking.user_id != self.user_id:
            raise BookingNotFound()

        if booking.status == BookingStatus.PAID:
            raise BookingNotPayable("Booking already paid")
        if booking.status != BookingStatus.PENDING_PAYMENTS:
            raise BookingNotPayable(f"Booking status is {booking.status.value}")
        if booking.expires_at <= datetime.now(timezone.utc):
            raise BookingNotPayable("Booking expired")

        try:
            await self.payment_service.get_first_by_filters(booking_id=booking_id)
        except NotFoundException:
            pass
        else:
            raise PaymentAlreadyExists()

        payment: Payment = await self.payment_service.create(
            **SPaymentCreate(
                booking_id=booking_id,
                external_id=Faker().uuid4(),
            ).to_dict()
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

        if booking.status == BookingStatus.PAID:
            if payment.status == PaymentStatus.SUCCESS:
                return SPaymentOut.from_model(payment)
            raise BookingNotPayable("Booking already paid")

        if booking.status != BookingStatus.PENDING_PAYMENTS:
            raise BookingNotPayable(f"Booking status is {booking.status.value}")

        if booking.expires_at <= datetime.now(timezone.utc):
            raise BookingNotPayable("Booking expired")

        updated_payment: Payment = await self.payment_service.update_by_id(payment_id, status=PaymentStatus.SUCCESS)
        await self.booking_service.set_booking_paid(updated_payment.booking_id)

        return SPaymentOut.from_model(updated_payment)
