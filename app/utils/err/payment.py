from app.utils.err.base.conflict import ConflictException
from app.utils.err.base.not_found import NotFoundException
from app.utils.err.base.service_unavailable import ServiceUnavailableException


class PaymentNotFound(NotFoundException):
    def __init__(self):
        super().__init__("Payment not found")


class PaymentAlreadyExists(ConflictException):
    def __init__(self):
        super().__init__("Payment already exists")


class PaymentProviderRejected(ConflictException):
    def __init__(self, detail: str = "Payment provider rejected operation"):
        super().__init__(detail)


class PaymentProviderUnavailable(ServiceUnavailableException):
    def __init__(self, operation: str):
        super().__init__(f"Payment provider is unavailable for {operation}")
