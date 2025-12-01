from app.models import Booking
from app.repositories.booking import BookingRepository
from app.services.base import BaseService


class BookingService(BaseService[Booking]):
    _repository = BookingRepository
