from app.utils.err.base.conflict import ConflictException


class InvalidTimeSlot(ConflictException):
    def __init__(self):
        super().__init__("Timeslot can not be created")
