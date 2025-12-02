from app.models import Payment
from app.repositories.payment import PaymentRepository
from app.services.base import BaseService


class PaymentService(BaseService[Payment]):
    _repository = PaymentRepository
