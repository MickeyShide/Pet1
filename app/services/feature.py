from app.models import Feature
from app.repositories.feature import FeatureRepository
from app.services.base import BaseService


class FeatureService(BaseService[Feature]):
    _repository = FeatureRepository
