import uuid

from app.config import settings
from app.db.base import new_session
from app.schemas.image import SImagePresignIn, SImagePresignOut
from app.services.business.base import BaseBusinessService
from app.services.image import ImageService
from app.utils.s3 import get_s3


def build_key(img_type: str, ext: str) -> str:
    uid = uuid.uuid4().hex
    return f"images/{img_type.lower()}/{uid}.{ext}"


def public_url(key: str) -> str:
    # локально; в проде лучше settings.S3_PUBLIC_BASE_URL
    base_url = settings.S3_PUBLIC_BASE_URL.rstrip("/")
    return f"{base_url}/{settings.S3_BUCKET}/{key}"


class ImageBusinessService(BaseBusinessService):
    image_service: ImageService

    @new_session()
    async def presign(self, payload: SImagePresignIn) -> SImagePresignOut:
        s3 = get_s3()

        key1 = build_key(payload.type.value, payload.ext)

        image = await self.image_service.create(type=payload.type, image1x=key1)

        upload_1x = s3.generate_presigned_url(
            ClientMethod="put_object",
            Params={
                "Bucket": settings.S3_BUCKET,
                "Key": key1,
                "ContentType": payload.mime,
            },
            ExpiresIn=600,  # 10 минут
        )

        return SImagePresignOut(
            id=image.id,
            upload_url=upload_1x,
            public_url=public_url(key1),
        )
