from app.services.business.base import BaseBusinessService
from app.services.image import ImageService


class ImageBusinessService(BaseBusinessService):
    image_service: ImageService
