from app.db.base import new_session
from app.models import Image, File
from app.models.image import ImageType
from app.schemas.image import SImageUploadIn, SImagePresignOut
from app.services.business.base import BaseBusinessService
from app.services.file import FileService
from app.services.image import ImageService
from app.services.location import LocationService
from app.services.room import RoomService


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
            room_id=room_id,
            location_id=None,
            payload=payload,
        )

    @new_session()
    async def upload_location_image(self, location_id: int, payload: SImageUploadIn) -> SImagePresignOut:
        await self.location_service.get_one_by_id(location_id)
        return await self._upload_image(
            scope="locations",
            owner_id=location_id,
            image_type=ImageType.LOCATION,
            room_id=None,
            location_id=location_id,
            payload=payload,
        )

    async def _upload_image(
        self,
        *,
        scope: str,
        owner_id: int,
        image_type: ImageType,
        room_id: int | None,
        location_id: int | None,
        payload: SImageUploadIn,
    ) -> SImagePresignOut:
        file, upload_url = await self.file_service.upload_image(
            user_id=self.user_id,
            scope=scope,
            owner_id=owner_id,
            payload=payload,
        )

        image = await self.image_service.create(
            type=image_type,
            image1x=file.public_url,
            image2x=None,
            file_id=file.id,
            room_id=room_id,
            location_id=location_id,
        )

        return SImagePresignOut(
            id=image.id,
            upload_url=upload_url,
            public_url=file.public_url,
        )

    @new_session()
    async def delete_image(self, image_id: int) -> None:
        image: Image = await self.image_service.get_one_by_id(image_id)
        file: File = await self.file_service.get_one_by_id(image.file_id)

        await self.file_service.delete_object(file.bucket, file.object_key)
        await self.image_service.delete_by_id(image.id)
        await self.file_service.delete_by_id(file.id)
