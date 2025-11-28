from app.models.base import BaseSQLModel

from .booking import Booking
from .timeslot import TimeSlot
from .room import Room
from .user import User
from .notificationlog import NotificationLog
from .payment import Payment
from .location import Location

from sqlmodel import SQLModel
__all__ = [
    "BaseSQLModel"
]