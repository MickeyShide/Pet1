from .base import BaseSQLModel


class Location(BaseSQLModel, table=True):
    __tablename__ = "locations"

    name: str
    address: str
    description: str