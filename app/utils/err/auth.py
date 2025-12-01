from app.utils.err.base.conflict import ConflictException


class EmailAlreadyTaken(ConflictException):
    def __init__(self):
        super().__init__("User with this email already exists")


class UsernameAlreadyTaken(ConflictException):
    def __init__(self):
        super().__init__("Username already taken")
