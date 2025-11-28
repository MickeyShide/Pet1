from app.models.timeslot import TimeSlot
from app.repositories.base import BaseRepository


class TimeSlotRepository(BaseRepository[TimeSlot]):
    _model_cls = TimeSlot
