from typing import Any

from starlette import status

from app.config import settings
from app.models import Booking
from app.celery_app.tasks import expire_booking_task
from app.overload import OverloadRejected, overload_controller, overload_guard

class CeleryManager:

    @staticmethod
    async def expire_booking(booking: Booking) -> dict[str, Any]:
        try:
            async with overload_guard("background_task_schedule"):
                result = expire_booking_task.apply_async(
                    args=[booking.id, booking.expires_at.isoformat()],
                    eta=booking.expires_at,
                )
                overload_controller.clear_dependency_degraded("rabbitmq")
                return result
        except OverloadRejected:
            raise
        except Exception as exc:
            overload_controller.mark_dependency_degraded("rabbitmq", "task_schedule_failed")
            raise OverloadRejected(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                error_code="dependency_degraded",
                message="rabbitmq is degraded",
                retry_after=settings.OVERLOAD_RETRY_AFTER_SECONDS,
                degraded_component="rabbitmq",
            ) from exc
