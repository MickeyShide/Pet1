from app.utils.err.base.conflict import ConflictError


class EmailAlreadyTaken(ConflictError):
    def __init__(self):
        super().__init__("User with this email already exists")


class UsernameAlreadyTaken(ConflictError):
    def __init__(self):
        super().__init__("Username already taken")
