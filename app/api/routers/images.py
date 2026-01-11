from fastapi import APIRouter
from starlette import status

from app.api import docs
from app.api.deps import AdminDepends
from app.services.business.images import ImageBusinessService

router = APIRouter(prefix="/images", tags=["Images"])


@router.delete(
    "/{image_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    description="Delete image by id",
    responses={
        status.HTTP_204_NO_CONTENT: {
            "description": "Image deleted",
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
                "image_not_found": docs.example(
                    "Image not found",
                    {"detail": "no_item_in_<class 'app.models.image.Image'>_with_1_id"},
                )
            },
        ),
    },
)
async def delete_image(image_id: int, token_data: AdminDepends) -> None:
    await ImageBusinessService(token_data=token_data).delete_image(image_id)
