from app.models.file import File
from app.repositories.base import BaseRepository


class FileRepository(BaseRepository[File]):
    _model_cls = File
