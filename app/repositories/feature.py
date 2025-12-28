from app.models.feature import Feature
from app.repositories.base import BaseRepository


class FeatureRepository(BaseRepository[Feature]):
    _model_cls = Feature
