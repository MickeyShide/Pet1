from sqlalchemy.exc import IntegrityError

from app.models import Location
from app.services.base import BaseService
from app.repositories.location import LocationRepository


class LocationService(BaseService[Location]):
    _repository = LocationRepository