from app.utils.err.base.conflict import ConflictException


class NotFlexibleTimeslotsType(ConflictException):
    def __init__(self):
        super().__init__("Timeslot type of this room ISNT flexible.")