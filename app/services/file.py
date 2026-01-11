import uuid

import anyio

from app.config import settings
from app.models.file import File, FileStatus
from app.repositories.file import FileRepository
from app.schemas.image import SImageUploadIn
from app.services.base import BaseService
from app.utils import s3 as s3_utils
from app.utils.file_utils import validate_content_type, validate_size, build_public_url, sanitize_filename


class FileService(BaseService[File]):
    _repository = FileRepository

    @staticmethod
    def build_key(scope: str, owner_id: int, ext: str) -> str:
        uid = uuid.uuid4().hex
        return f"images/{scope}/{owner_id}/{uid}.{ext}"

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

    async def upload_image(
        self,
        user_id: int,
        scope: str,
        owner_id: int,
        payload: SImageUploadIn,
    ) -> tuple[File, str]:
        """
        returns File object and upload url
        """
        validate_content_type(payload.mime, settings.files_allowed_content_types)
        validate_size(
            "PRESIGNED",
            payload.size,
            settings.S3_MAX_UPLOAD_BYTES_PROXY,
            settings.S3_MAX_UPLOAD_BYTES_PRESIGNED,
        )
        ext = payload.ext.strip().lower().lstrip(".") or "bin"
        key = self.build_key(scope, owner_id, ext)
        bucket = settings.s3_public_bucket
        public_url = build_public_url(settings.S3_PUBLIC_BASE_URL, bucket, key)

        original_name = sanitize_filename(payload.original_name or f"image.{ext}")

        file = await self.create(
            user_id=user_id,
            bucket=bucket,
            object_key=key,
            original_name=original_name,
            content_type=payload.mime,
            size_bytes=payload.size,
            checksum_sha256=None,
            status=FileStatus.PENDING,
            is_public=True,
            public_url=public_url,
            meta={},
        )

        upload_url = await self.presign_upload_put(
            bucket,
            key,
            payload.mime,
            settings.S3_PRESIGN_EXPIRES_SECONDS,
        )

        return file, upload_url
