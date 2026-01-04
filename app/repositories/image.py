from app.models import Image
from app.repositories.base import BaseRepository


class ImageRepository(BaseRepository[Image]):
    _model_cls = Image
