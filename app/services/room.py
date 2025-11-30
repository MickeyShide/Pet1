from app.models import Room
from app.repositories.room import RoomRepository
from app.services.base import BaseService


class RoomService(BaseService[Room]):
    _repository = RoomRepository
