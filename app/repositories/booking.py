from app.models import Booking
from app.repositories.base import BaseRepository


class BookingRepository(BaseRepository[Booking]):
    _model_cls = Booking
