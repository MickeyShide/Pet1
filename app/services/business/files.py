from __future__ import annotations

import uuid
from datetime import datetime, timezone, timedelta

from app.config import settings
from app.db.base import new_session
from app.models.file import FileStatus
from app.schemas.file import (
    SFileInitUploadIn,
    SFileInitUploadOut,
    SFileUploadInstruction,
    SFileDownloadInstruction,
    SFileOut,
)
from app.services.business.base import BaseBusinessService
from app.services.file import FileService
from app.utils.err.base.conflict import ConflictException
from app.utils.file_utils import (
    sanitize_filename,
    validate_content_type,
    validate_size,
    build_object_key,
    build_public_url,
)


class FileBusinessService(BaseBusinessService):
    file_service: FileService

    @new_session()
    async def init_upload(self, payload: SFileInitUploadIn) -> SFileInitUploadOut:
        now = datetime.now(timezone.utc)

        # clear name from .. / \\ etc
        safe_name = sanitize_filename(payload.original_name)

        # checks content type is in white list
        validate_content_type(payload.content_type, settings.files_allowed_content_types)

        # checks file size limits
        validate_size(
            payload.mode.value,
            payload.size_bytes,
            settings.S3_MAX_UPLOAD_BYTES_PROXY,
            settings.S3_MAX_UPLOAD_BYTES_PRESIGNED,
        )
        # TEMP KEY! only for creating object to get file ID for REAL key
        temp_key = f"pending/{uuid.uuid4().hex}"
        bucket = settings.s3_public_bucket if payload.is_public else settings.S3_BUCKET

        # create file in db
        file = await self.file_service.create(
            user_id=self.user_id,
            bucket=bucket,
            object_key=temp_key,
            original_name=payload.original_name,
            content_type=payload.content_type,
            size_bytes=payload.size_bytes,
            checksum_sha256=payload.checksum_sha256,
            status=FileStatus.PENDING,
            meta={},
            is_public=payload.is_public,
        )

        # set real key
        object_key = build_object_key(settings.APP_ENV, self.user_id, now, file.id, safe_name)
        file = await self.file_service.update_by_id(file.id, object_key=object_key)

        # upload instruction for PROXY upload mode
        upload = SFileUploadInstruction(
            url=f"/files/{file.id}/upload",
            method="PUT",
            headers={},
            expires_at=None,
        )

        # upload instruction for PRESIGNED upload mode
        if payload.mode.value == "PRESIGNED":
            url = await self.file_service.presign_upload_put(
                file.bucket,
                file.object_key,
                file.content_type,
                settings.S3_PRESIGN_EXPIRES_SECONDS,
            )
            upload = SFileUploadInstruction(
                url=url,
                method="PUT",
                headers={"Content-Type": file.content_type},
                expires_at=now + timedelta(seconds=settings.S3_PRESIGN_EXPIRES_SECONDS),
            )

        public_url = None
        if file.is_public:
            public_url = build_public_url(settings.S3_PUBLIC_BASE_URL, file.bucket, file.object_key)

        return SFileInitUploadOut(
            file_id=file.id,
            status=file.status,
            bucket=file.bucket,
            object_key=file.object_key,
            upload=upload,
            public_url=public_url,
        )

    @new_session(readonly=True)
    async def presign_download(self, file_id: int) -> SFileDownloadInstruction:
        # find file
        file = await self.file_service.get_first_by_filters(id=file_id, user_id=self.user_id)

        # if not uploaded yet
        if file.status != FileStatus.UPLOADED:
            raise ConflictException("file_not_uploaded")

        # create download URL
        now = datetime.now(timezone.utc)
        url = await self.file_service.presign_download_get(
            file.bucket,
            file.object_key,
            settings.S3_PRESIGN_EXPIRES_SECONDS,
        )

        return SFileDownloadInstruction(
            url=url,
            method="GET",
            expires_at=now + timedelta(seconds=settings.S3_PRESIGN_EXPIRES_SECONDS),
        )

    @new_session(readonly=True)
    async def get(self, file_id: int) -> SFileOut:
        file = await self.file_service.get_first_by_filters(id=file_id, user_id=self.user_id)
        payload = SFileOut.model_validate(file)
        if file.is_public:
            return payload.model_copy(
                update={
                    "public_url": build_public_url(
                        settings.S3_PUBLIC_BASE_URL,
                        file.bucket,
                        file.object_key,
                    )
                }
            )
        return payload
