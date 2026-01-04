from app.models import Image
from app.repositories.image import ImageRepository
from app.services.base import BaseService


class ImageService(BaseService[Image]):
    _repository = ImageRepository
