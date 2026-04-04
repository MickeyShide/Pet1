from datetime import datetime, timezone
from decimal import Decimal
from typing import Callable, Awaitable, TypeVar

from app.db.base import new_session
from app.config import settings
from app.integrations.payment_gateway import (
    MockPaymentGateway,
    PaymentGatewayRetryableError,
    PaymentGatewayNonRetryableError,
    retry_with_backoff,
)
from app.models import Payment, Booking
from app.models.booking import BookingStatus
from app.models.payment import PaymentStatus
from app.schemas.payment import SPaymentCreate, SPaymentOut
from app.services.booking import BookingService
from app.services.business.base import BaseBusinessService
from app.services.payment import PaymentService
from app.utils.err.base.not_found import NotFoundException
from app.utils.err.booking import BookingNotFound, BookingNotPayable
from app.utils.err.payment import (
    PaymentNotFound,
    PaymentAlreadyExists,
    PaymentProviderRejected,
    PaymentProviderUnavailable,
)


RT = TypeVar("RT")


class PaymentBusinessService(BaseBusinessService):
    payment_service: PaymentService
    booking_service: BookingService

    def _get_payment_gateway(self) -> MockPaymentGateway:
        return MockPaymentGateway()

    async def _call_gateway_with_retry(
        self,
        operation_name: str,
        operation: Callable[[], Awaitable[RT]],
    ) -> RT:
        try:
            return await retry_with_backoff(
                operation,
                max_attempts=settings.PAYMENT_RETRY_MAX_ATTEMPTS,
                base_delay_seconds=settings.PAYMENT_RETRY_BASE_DELAY_SECONDS,
                max_delay_seconds=settings.PAYMENT_RETRY_MAX_DELAY_SECONDS,
                is_retryable=lambda exc: isinstance(exc, PaymentGatewayRetryableError),
            )
        except PaymentGatewayRetryableError as exc:
            raise PaymentProviderUnavailable(operation_name) from exc
        except PaymentGatewayNonRetryableError as exc:
            raise PaymentProviderRejected(str(exc)) from exc

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
        payment_gateway = self._get_payment_gateway()

        external_id = await self._call_gateway_with_retry(
            operation_name="create_payment",
            operation=lambda: payment_gateway.create_payment(
                booking_id=booking_id,
                amount=Decimal(booking.total_price),
            ),
        )

        payment: Payment = await self.payment_service.create(
            **SPaymentCreate(
                booking_id=booking_id,
                external_id=external_id,
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
        payment_gateway = self._get_payment_gateway()

        await self._call_gateway_with_retry(
            operation_name="confirm_payment",
            operation=lambda: payment_gateway.confirm_payment(
                external_id=payment.external_id,
                amount=Decimal(booking.total_price),
            ),
        )

        updated_payment: Payment = await self.payment_service.update_by_id(payment_id, status=PaymentStatus.SUCCESS)
        await self.booking_service.set_booking_paid(updated_payment.booking_id)

        return SPaymentOut.from_model(updated_payment)
