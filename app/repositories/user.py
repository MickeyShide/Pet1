from app.models.user import User
from app.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    _model_cls = User
