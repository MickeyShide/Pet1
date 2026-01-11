from typing import Any

from app.models import Booking
from app.celery_app.tasks import expire_booking_task

class CeleryManager:

    @staticmethod
    async def expire_booking(booking: Booking) -> dict[str, Any]:
        return expire_booking_task.apply_async(args=[booking.id], eta=booking.expires_at)