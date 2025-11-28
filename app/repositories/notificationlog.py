from app.models.notificationlog import NotificationLog
from app.repositories.base import BaseRepository


class NotificationLogRepository(BaseRepository[NotificationLog]):
    _model_cls = NotificationLog
