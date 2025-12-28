from app.db.base import new_session
from app.models import Feature
from app.schemas.feature import SFeatureCreate, SFeatureOut, SFeatureUpdate
from app.services.business.base import BaseBusinessService
from app.services.feature import FeatureService


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
        feature: Feature = await self.feature_service.create(**feature_data.model_dump())
        return SFeatureOut.from_model(feature)

    @new_session()
    async def update_by_id(self, feature_id: int, feature_data: SFeatureUpdate) -> SFeatureOut:
        feature: Feature = await self.feature_service.update_by_id(
            feature_id,
            **feature_data.model_dump(exclude_unset=True),
        )
        return SFeatureOut.from_model(feature)

    @new_session()
    async def delete_by_id(self, feature_id: int) -> None:
        await self.feature_service.delete_by_id(feature_id)
