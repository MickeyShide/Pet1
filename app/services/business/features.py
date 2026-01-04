from starlette import status
from starlette.exceptions import HTTPException

from app.db.base import new_session
from app.models.feature import FeatureType
from app.models import Feature
from app.schemas.feature import SFeatureCreate, SFeatureOut, SFeatureUpdate
from app.services.business.base import BaseBusinessService
from app.services.feature import FeatureService
from app.utils.cache import CacheService, keys


class FeatureBusinessService(BaseBusinessService):
    feature_service: FeatureService

    @new_session(readonly=True)
    async def get_all(self) -> list[SFeatureOut]:
        features = await self.feature_service.get_all()
        return [SFeatureOut.from_model(feature) for feature in features]

    @new_session(readonly=True)
    async def get_by_id(self, feature_id: int) -> SFeatureOut:
        feature: Feature = await self.feature_service.get_one_by_id(feature_id)
        return SFeatureOut.from_model(feature)

    @new_session()
    async def create(self, feature_data: SFeatureCreate) -> SFeatureOut:
        feature: Feature = await self.feature_service.create(**feature_data.to_dict())
        await CacheService().delete_pattern(keys.locations_all())
        return SFeatureOut.from_model(feature)

    @new_session()
    async def update_by_id(self, feature_id: int, feature_data: SFeatureUpdate) -> SFeatureOut:
        existing: Feature = await self.feature_service.get_one_by_id(feature_id)
        fields_set = feature_data.model_fields_set
        if not fields_set:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="No fields provided for update",
            )

        new_type = feature_data.type if "type" in fields_set else existing.type
        new_room_id = feature_data.room_id if "room_id" in fields_set else existing.room_id
        new_location_id = feature_data.location_id if "location_id" in fields_set else existing.location_id

        if new_type == FeatureType.ROOM:
            if new_room_id is None or new_location_id is not None:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="ROOM feature requires room_id and no location_id",
                )
        if new_type == FeatureType.LOCATION:
            if new_location_id is None or new_room_id is not None:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="LOCATION feature requires location_id and no room_id",
                )

        feature: Feature = await self.feature_service.update_by_id(
            feature_id,
            **feature_data.to_dict(),
        )
        await CacheService().delete_pattern(keys.locations_all())
        return SFeatureOut.from_model(feature)

    @new_session()
    async def delete_by_id(self, feature_id: int) -> None:
        await self.feature_service.delete_by_id(feature_id)
        await CacheService().delete_pattern(keys.locations_all())
