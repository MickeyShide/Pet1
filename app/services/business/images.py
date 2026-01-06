import uuid

from app.config import settings
from app.db.base import new_session
from app.models.file import FileStatus
from app.models.image import ImageType
from app.schemas.image import SImageUploadIn, SImagePresignOut
from app.services.business.base import BaseBusinessService
from app.services.file import FileService
from app.services.image import ImageService
from app.services.location import LocationService
from app.services.room import RoomService
from app.utils.file_utils import (
    build_public_url,
    sanitize_filename,
    validate_content_type,
    validate_size,
)


def build_key(scope: str, owner_id: int, ext: str) -> str:
    uid = uuid.uuid4().hex
    return f"images/{scope}/{owner_id}/{uid}.{ext}"


class ImageBusinessService(BaseBusinessService):
    image_service: ImageService
    file_service: FileService
    room_service: RoomService
    location_service: LocationService

    @new_session()
    async def upload_room_image(self, room_id: int, payload: SImageUploadIn) -> SImagePresignOut:
        await self.room_service.get_one_by_id(room_id)
        return await self._upload_image(
            scope="rooms",
            owner_id=room_id,
            image_type=ImageType.ROOM,
            payload=payload,
            room_id=room_id,
            location_id=None,
        )

    @new_session()
    async def upload_location_image(self, location_id: int, payload: SImageUploadIn) -> SImagePresignOut:
        await self.location_service.get_one_by_id(location_id)
        return await self._upload_image(
            scope="locations",
            owner_id=location_id,
            image_type=ImageType.LOCATION,
            payload=payload,
            room_id=None,
            location_id=location_id,
        )

    async def _upload_image(
            self,
            *,
            scope: str,
            owner_id: int,
            image_type: ImageType,
            payload: SImageUploadIn,
            room_id: int | None,
            location_id: int | None,
    ) -> SImagePresignOut:
        validate_content_type(payload.mime, settings.files_allowed_content_types)
        validate_size(
            "PRESIGNED",
            payload.size,
            settings.S3_MAX_UPLOAD_BYTES_PROXY,
            settings.S3_MAX_UPLOAD_BYTES_PRESIGNED,
        )
        key = build_key(scope, owner_id, payload.ext)
        bucket = settings.s3_public_bucket
        image_url = build_public_url(settings.S3_PUBLIC_BASE_URL, bucket, key)

        original_name = payload.original_name or f"image.{payload.ext}"
        original_name = sanitize_filename(original_name)
        file = await self.file_service.create(
            user_id=self.user_id,
            bucket=bucket,
            object_key=key,
            original_name=original_name,
            content_type=payload.mime,
            size_bytes=payload.size,
            checksum_sha256=None,
            status=FileStatus.PENDING,
            is_public=True,
            public_url=image_url,
            meta={},
        )

        image = await self.image_service.create(
            type=image_type,
            image1x=image_url,
            image2x=None,
            file_id=file.id,
            room_id=room_id,
            location_id=location_id,
        )

        upload_url = await self.file_service.presign_upload_put(
            bucket,
            key,
            payload.mime,
            settings.S3_PRESIGN_EXPIRES_SECONDS,
        )

        return SImagePresignOut(
            id=image.id,
            upload_url=upload_url,
            public_url=image_url,
        )

    @new_session()
    async def delete_image(self, image_id: int) -> None:
        image = await self.image_service.get_one_by_id(image_id)
        file = await self.file_service.get_one_by_id(image.file_id)

        await self.file_service.delete_object(file.bucket, file.object_key)
        await self.image_service.delete_by_id(image.id)
        await self.file_service.delete_by_id(file.id)
