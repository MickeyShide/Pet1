from app.utils.err.base.conflict import ConflictException
from app.utils.err.base.too_many import TooManyRequestsException


class EmailAlreadyTaken(ConflictException):
    def __init__(self):
        super().__init__("User with this email already exists")


class UsernameAlreadyTaken(ConflictException):
    def __init__(self):
        super().__init__("Username already taken")


class TooManyAttempts(TooManyRequestsException):
    def __init__(self):
        super().__init__("Too many auth attempts")
