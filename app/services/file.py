import anyio

from app.models.file import File
from app.repositories.file import FileRepository
from app.services.base import BaseService
from app.utils import s3 as s3_utils

class FileService(BaseService[File]):
    _repository = FileRepository

    async def presign_upload_put(self, bucket: str, key: str, content_type: str, expires: int) -> str:
        return await anyio.to_thread.run_sync(
            s3_utils.presign_put_object,
            bucket,
            key,
            content_type,
            expires,
        )

    async def presign_download_get(self, bucket: str, key: str, expires: int) -> str:
        return await anyio.to_thread.run_sync(
            s3_utils.presign_get_object,
            bucket,
            key,
            expires,
        )

    async def head(self, bucket: str, key: str) -> dict:
        return await anyio.to_thread.run_sync(
            s3_utils.head_object,
            bucket,
            key,
        )

    async def delete_object(self, bucket: str, key: str) -> None:
        await anyio.to_thread.run_sync(
            s3_utils.delete_object,
            bucket,
            key,
        )
