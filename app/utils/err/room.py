from app.utils.err.base.conflict import ConflictException


class NotFlexibleTimeslotsType(ConflictException):
    def __init__(self):
        super().__init__("Timeslot type of this room ISNT flexible.")

class InvalidBookingDuration(ConflictException):
    def __init__(self, min_minutes: int, step_minutes: int):
        super().__init__(
            f"Duration must be >= {min_minutes} and aligned to {step_minutes} minutes."
        )
