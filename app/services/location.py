from app.models import Location
from app.repositories.location import LocationRepository
from app.services.base import BaseService


class LocationService(BaseService[Location]):
    _repository = LocationRepository
