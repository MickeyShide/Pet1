from typing import List

from fastapi import APIRouter
from starlette import status

from app.api.deps import AdminDepends
from app.schemas.feature import SFeatureCreate, SFeatureOut, SFeatureUpdate
from app.services.business.features import FeatureBusinessService

router = APIRouter(prefix="/features", tags=["Features"])


@router.get(
    path="",
    response_model=List[SFeatureOut],
    status_code=status.HTTP_200_OK,
    description="Return all features",
)
async def get_all_features_route() -> List[SFeatureOut]:
    return await FeatureBusinessService().get_all()


@router.get(
    path="/{feature_id}",
    response_model=SFeatureOut,
    status_code=status.HTTP_200_OK,
    description="Return feature by id",
)
async def get_feature_by_id_route(feature_id: int) -> SFeatureOut:
    return await FeatureBusinessService().get_by_id(feature_id)


@router.post(
    path="",
    response_model=SFeatureOut,
    status_code=status.HTTP_200_OK,
    description="Create new feature",
)
async def create_feature_route(feature_data: SFeatureCreate, token_data: AdminDepends) -> SFeatureOut:
    return await FeatureBusinessService().create(feature_data)


@router.patch(
    path="/{feature_id}",
    response_model=SFeatureOut,
    status_code=status.HTTP_200_OK,
    description="Update existing feature",
)
async def update_feature_route(
    feature_id: int,
    feature_data: SFeatureUpdate,
    token_data: AdminDepends,
) -> SFeatureOut:
    return await FeatureBusinessService().update_by_id(feature_id, feature_data)


@router.delete(
    path="/{feature_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    description="Delete existing feature",
)
async def delete_feature_route(feature_id: int, token_data: AdminDepends) -> None:
    return await FeatureBusinessService().delete_by_id(feature_id)
