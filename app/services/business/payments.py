from datetime import datetime, timezone
from decimal import Decimal
import logging
from time import perf_counter
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
from app.observability.metrics import (
    dec_business_operation_in_progress,
    inc_business_operation_in_progress,
    observe_business_operation_duration,
    observe_booking_payment_confirm,
    observe_payment_gateway_error,
    observe_payment_gateway_operation,
    observe_payment_gateway_retry,
)
from app.overload import overload_controller, overload_protected
from app.utils.err.base.not_found import NotFoundException
from app.utils.err.booking import BookingNotFound, BookingNotPayable
from app.utils.err.payment import (
    PaymentNotFound,
    PaymentAlreadyExists,
    PaymentProviderRejected,
    PaymentProviderUnavailable,
)


RT = TypeVar("RT")
logger = logging.getLogger("app.business.payments")


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
        started_at = perf_counter()

        def _on_retry(attempt: int, delay_seconds: float, exc: Exception) -> None:
            error_type = type(exc).__name__
            observe_payment_gateway_retry(operation=operation_name, error_type=error_type)
            logger.warning(
                "payment_gateway_retry_scheduled",
                extra={
                    "event": "payment_gateway_retry_scheduled",
                    "operation": operation_name,
                    "attempt": attempt,
                    "retry_delay_ms": round(delay_seconds * 1000, 3),
                    "error_code": error_type,
                    "anomaly_type": "payment_gateway_retry",
                },
            )

        try:
            result = await retry_with_backoff(
                operation,
                max_attempts=settings.PAYMENT_RETRY_MAX_ATTEMPTS,
                base_delay_seconds=settings.PAYMENT_RETRY_BASE_DELAY_SECONDS,
                max_delay_seconds=settings.PAYMENT_RETRY_MAX_DELAY_SECONDS,
                is_retryable=lambda exc: isinstance(exc, PaymentGatewayRetryableError),
                on_retry=_on_retry,
            )
            duration_seconds = perf_counter() - started_at
            observe_payment_gateway_operation(
                operation=operation_name,
                result="success",
                duration_seconds=duration_seconds,
            )
            overload_controller.clear_dependency_degraded("payment_gateway")
            if duration_seconds >= settings.OBS_HIGH_PAYMENT_GATEWAY_SECONDS:
                logger.warning(
                    "payment_gateway_slow",
                    extra={
                        "event": "payment_gateway_slow",
                        "operation": operation_name,
                        "duration_ms": round(duration_seconds * 1000, 3),
                        "threshold_ms": round(settings.OBS_HIGH_PAYMENT_GATEWAY_SECONDS * 1000, 3),
                        "anomaly_type": "payment_gateway_slow",
                    },
                )
            return result
        except PaymentGatewayRetryableError as exc:
            overload_controller.mark_dependency_degraded("payment_gateway", "retry_exhausted")
            duration_seconds = perf_counter() - started_at
            error_type = type(exc).__name__
            observe_payment_gateway_error(operation=operation_name, error_type=error_type)
            observe_payment_gateway_operation(
                operation=operation_name,
                result="retry_exhausted",
                duration_seconds=duration_seconds,
            )
            raise PaymentProviderUnavailable(operation_name) from exc
        except PaymentGatewayNonRetryableError as exc:
            overload_controller.clear_dependency_degraded("payment_gateway")
            duration_seconds = perf_counter() - started_at
            error_type = type(exc).__name__
            observe_payment_gateway_error(operation=operation_name, error_type=error_type)
            observe_payment_gateway_operation(
                operation=operation_name,
                result="rejected",
                duration_seconds=duration_seconds,
            )
            raise PaymentProviderRejected(str(exc)) from exc
        except Exception as exc:
            duration_seconds = perf_counter() - started_at
            observe_payment_gateway_error(operation=operation_name, error_type=type(exc).__name__)
            observe_payment_gateway_operation(
                operation=operation_name,
                result="error",
                duration_seconds=duration_seconds,
            )
            raise

    @overload_protected("payment_create")
    @new_session()
    async def create_payment(self, booking_id: int) -> SPaymentOut:
        operation = "create_payment"
        started_at = perf_counter()
        result_label = "error"
        inc_business_operation_in_progress(operation)
        logger.info(
            "payment_create_started",
            extra={
                "event": "payment_create_started",
                "operation": operation,
                "booking_id": booking_id,
            },
        )
        try:
            booking = await self.booking_service.get_one_by_id(booking_id)

            if not self.admin and booking.user_id != self.user_id:
                result_label = "not_found"
                raise BookingNotFound()

            if booking.status == BookingStatus.PAID:
                result_label = "conflict"
                raise BookingNotPayable("Booking already paid")
            if booking.status != BookingStatus.PENDING_PAYMENTS:
                result_label = "conflict"
                raise BookingNotPayable(f"Booking status is {booking.status.value}")
            if booking.expires_at <= datetime.now(timezone.utc):
                result_label = "conflict"
                raise BookingNotPayable("Booking expired")

            try:
                await self.payment_service.get_first_by_filters(booking_id=booking_id)
            except NotFoundException:
                pass
            else:
                result_label = "conflict"
                raise PaymentAlreadyExists()
            payment_gateway = self._get_payment_gateway()

            external_id = await self._call_gateway_with_retry(
                operation_name=operation,
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
            result_label = "success"
            logger.info(
                "payment_created",
                extra={
                    "event": "payment_created",
                    "operation": operation,
                    "booking_id": booking_id,
                    "payment_id": payment.id,
                    "external_id": payment.external_id,
                },
            )
            return SPaymentOut.from_model(payment)
        finally:
            duration_seconds = perf_counter() - started_at
            observe_business_operation_duration(
                operation=operation,
                result=result_label,
                duration_seconds=duration_seconds,
            )
            if duration_seconds >= settings.OBS_SLOW_BUSINESS_OPERATION_SECONDS:
                logger.warning(
                    "business_operation_slow",
                    extra={
                        "event": "business_operation_slow",
                        "operation": operation,
                        "booking_id": booking_id,
                        "duration_ms": round(duration_seconds * 1000, 3),
                        "threshold_ms": round(settings.OBS_SLOW_BUSINESS_OPERATION_SECONDS * 1000, 3),
                        "result": result_label,
                        "anomaly_type": "slow_business_operation",
                    },
                )
            dec_business_operation_in_progress(operation)

    @overload_protected("payment_confirm")
    @new_session()
    async def confirm_payment(self, payment_id: int) -> SPaymentOut:
        # In-flight op.
        operation = "confirm_payment"
        started_at = perf_counter()
        result_label = "error"
        inc_business_operation_in_progress(operation)
        try:
            try:
                payment: Payment = await self.payment_service.get_one_by_id(payment_id)
                booking: Booking = await self.booking_service.get_one_by_id(payment.booking_id)
                if not self.admin and booking.user_id != self.user_id:
                    # Hide foreign payment.
                    result_label = "not_found"
                    raise PaymentNotFound()
            except NotFoundException:
                result_label = "not_found"
                observe_booking_payment_confirm(result="failed", source="service", operation="confirm_payment")
                raise PaymentNotFound()

            if booking.status == BookingStatus.PAID:
                if payment.status == PaymentStatus.SUCCESS:
                    # Idempotent success.
                    result_label = "success"
                    observe_booking_payment_confirm(result="success", source="service", operation="confirm_payment")
                    return SPaymentOut.from_model(payment)
                result_label = "conflict"
                observe_booking_payment_confirm(result="conflict", source="service", operation="confirm_payment")
                raise BookingNotPayable("Booking already paid")

            if booking.status != BookingStatus.PENDING_PAYMENTS:
                result_label = "conflict"
                observe_booking_payment_confirm(result="conflict", source="service", operation="confirm_payment")
                raise BookingNotPayable(f"Booking status is {booking.status.value}")

            if booking.expires_at <= datetime.now(timezone.utc):
                result_label = "conflict"
                observe_booking_payment_confirm(result="conflict", source="service", operation="confirm_payment")
                raise BookingNotPayable("Booking expired")
            payment_gateway = self._get_payment_gateway()

            await self._call_gateway_with_retry(
                operation_name=operation,
                operation=lambda: payment_gateway.confirm_payment(
                    external_id=payment.external_id,
                    amount=Decimal(booking.total_price),
                ),
            )

            updated_payment: Payment = await self.payment_service.update_by_id(payment_id, status=PaymentStatus.SUCCESS)
            await self.booking_service.set_booking_paid(updated_payment.booking_id)

            # Success path.
            result_label = "success"
            observe_booking_payment_confirm(result="success", source="service", operation="confirm_payment")
            logger.info(
                "payment_confirmed",
                extra={
                    "event": "payment_confirmed",
                    "operation": operation,
                    "booking_id": updated_payment.booking_id,
                    "payment_id": updated_payment.id,
                },
            )
            return SPaymentOut.from_model(updated_payment)
        finally:
            duration_seconds = perf_counter() - started_at
            observe_business_operation_duration(
                operation=operation,
                result=result_label,
                duration_seconds=duration_seconds,
            )
            if duration_seconds >= settings.OBS_SLOW_BUSINESS_OPERATION_SECONDS:
                logger.warning(
                    "business_operation_slow",
                    extra={
                        "event": "business_operation_slow",
                        "operation": operation,
                        "payment_id": payment_id,
                        "duration_ms": round(duration_seconds * 1000, 3),
                        "threshold_ms": round(settings.OBS_SLOW_BUSINESS_OPERATION_SECONDS * 1000, 3),
                        "result": result_label,
                        "anomaly_type": "slow_business_operation",
                    },
                )
            dec_business_operation_in_progress(operation)
