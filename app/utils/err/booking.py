from app.utils.err.base.conflict import ConflictException
from app.utils.err.base.not_found import NotFoundException


class SlotAlreadyTaken(ConflictException):
    def __init__(self):
        super().__init__("Timeslot already taken")


class TimeSlotNotFound(NotFoundException):
    def __init__(self):
        super().__init__("Timeslot not found")


class BookingNotFound(NotFoundException):
    def __init__(self):
        super().__init__("Booking not found")
