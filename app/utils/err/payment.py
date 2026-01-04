from app.utils.err.base.conflict import ConflictException
from app.utils.err.base.not_found import NotFoundException


class PaymentNotFound(NotFoundException):
    def __init__(self):
        super().__init__("Payment not found")


class PaymentAlreadyExists(ConflictException):
    def __init__(self):
        super().__init__("Payment already exists")
