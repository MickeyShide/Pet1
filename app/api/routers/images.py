from fastapi import APIRouter
from starlette import status

from app.api.deps import AdminDepends
from app.services.business.images import ImageBusinessService

router = APIRouter(prefix="/images", tags=["Images"])


@router.delete(
    "/{image_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    description="Delete image by id",
)
async def delete_image(image_id: int, token_data: AdminDepends) -> None:
    await ImageBusinessService(token_data=token_data).delete_image(image_id)
