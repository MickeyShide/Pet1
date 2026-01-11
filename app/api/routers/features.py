from typing import List

from fastapi import APIRouter
from starlette import status

from app.api import docs
from app.api.deps import AdminDepends
from app.schemas.feature import SFeatureCreate, SFeatureOut, SFeatureUpdate
from app.services.business.features import FeatureBusinessService

router = APIRouter(prefix="/features", tags=["Features"])


@router.get(
    path="",
    response_model=List[SFeatureOut],
    status_code=status.HTTP_200_OK,
    description="Return all features",
    responses={
        status.HTTP_200_OK: docs.response_with_example(
            "Features",
            [docs.FEATURE_ROOM_EXAMPLE],
            model=List[SFeatureOut],
        ),
    },
)
async def get_all_features_route() -> List[SFeatureOut]:
    return await FeatureBusinessService().get_all()


@router.get(
    path="/{feature_id}",
    response_model=SFeatureOut,
    status_code=status.HTTP_200_OK,
    description="Return feature by id",
    responses={
        status.HTTP_200_OK: docs.response_with_example(
            "Feature",
            docs.FEATURE_ROOM_EXAMPLE,
            model=SFeatureOut,
        ),
        status.HTTP_404_NOT_FOUND: docs.error_response(
            "Not Found",
            {
                "feature_not_found": docs.example(
                    "Feature not found",
                    {"detail": "no_item_in_<class 'app.models.feature.Feature'>_with_1_id"},
                )
            },
        ),
    },
)
async def get_feature_by_id_route(feature_id: int) -> SFeatureOut:
    return await FeatureBusinessService().get_by_id(feature_id)


@router.post(
    path="",
    response_model=SFeatureOut,
    status_code=status.HTTP_200_OK,
    description="Create new feature",
    responses={
        status.HTTP_200_OK: docs.response_with_example(
            "Feature created",
            docs.FEATURE_ROOM_EXAMPLE,
            model=SFeatureOut,
        ),
        status.HTTP_401_UNAUTHORIZED: docs.error_response(
            "Unauthorized",
            {
                "missing_access_token": docs.example(
                    "Missing access token",
                    {"detail": "Missing access token"},
                ),
                "invalid_access_token": docs.example(
                    "Invalid access token",
                    {"detail": "Invalid access token"},
                ),
            },
        ),
        status.HTTP_403_FORBIDDEN: docs.error_response(
            "Forbidden",
            {
                "not_allowed": docs.example(
                    "Not allowed",
                    {"detail": "Not allowed"},
                )
            },
        ),
        status.HTTP_422_UNPROCESSABLE_ENTITY: docs.error_response(
            "Validation Error",
            {
                "invalid_payload": docs.example(
                    "Validation error",
                    docs.VALIDATION_ERROR_EXAMPLE,
                )
            },
        ),
    },
)
async def create_feature_route(feature_data: SFeatureCreate, token_data: AdminDepends) -> SFeatureOut:
    return await FeatureBusinessService().create(feature_data)


@router.patch(
    path="/{feature_id}",
    response_model=SFeatureOut,
    status_code=status.HTTP_200_OK,
    description="Update existing feature",
    responses={
        status.HTTP_200_OK: docs.response_with_example(
            "Feature updated",
            docs.FEATURE_ROOM_EXAMPLE,
            model=SFeatureOut,
        ),
        status.HTTP_401_UNAUTHORIZED: docs.error_response(
            "Unauthorized",
            {
                "missing_access_token": docs.example(
                    "Missing access token",
                    {"detail": "Missing access token"},
                ),
                "invalid_access_token": docs.example(
                    "Invalid access token",
                    {"detail": "Invalid access token"},
                ),
            },
        ),
        status.HTTP_403_FORBIDDEN: docs.error_response(
            "Forbidden",
            {
                "not_allowed": docs.example(
                    "Not allowed",
                    {"detail": "Not allowed"},
                )
            },
        ),
        status.HTTP_404_NOT_FOUND: docs.error_response(
            "Not Found",
            {
                "feature_not_found": docs.example(
                    "Feature not found",
                    {"detail": "no_item_in_<class 'app.models.feature.Feature'>_with_1_id"},
                )
            },
        ),
        status.HTTP_422_UNPROCESSABLE_ENTITY: docs.error_response(
            "Validation Error",
            {
                "no_fields": docs.example(
                    "No fields provided for update",
                    {"detail": "No fields provided for update"},
                ),
                "invalid_payload": docs.example(
                    "Validation error",
                    docs.VALIDATION_ERROR_EXAMPLE,
                ),
            },
        ),
    },
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
    responses={
        status.HTTP_204_NO_CONTENT: {
            "description": "Feature deleted",
        },
        status.HTTP_401_UNAUTHORIZED: docs.error_response(
            "Unauthorized",
            {
                "missing_access_token": docs.example(
                    "Missing access token",
                    {"detail": "Missing access token"},
                ),
                "invalid_access_token": docs.example(
                    "Invalid access token",
                    {"detail": "Invalid access token"},
                ),
            },
        ),
        status.HTTP_403_FORBIDDEN: docs.error_response(
            "Forbidden",
            {
                "not_allowed": docs.example(
                    "Not allowed",
                    {"detail": "Not allowed"},
                )
            },
        ),
        status.HTTP_404_NOT_FOUND: docs.error_response(
            "Not Found",
            {
                "feature_not_found": docs.example(
                    "Feature not found",
                    {"detail": "no_item_in_<class 'app.models.feature.Feature'>_with_1_id"},
                )
            },
        ),
    },
)
async def delete_feature_route(feature_id: int, token_data: AdminDepends) -> None:
    return await FeatureBusinessService().delete_by_id(feature_id)
