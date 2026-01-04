from fastapi import APIRouter

from app.api.deps import UserDepends
from app.schemas.image import SImagePresignIn, SImagePresignOut
from app.services.business.images import ImageBusinessService

router = APIRouter(prefix="/images", tags=["Images"])


@router.post("/presign", response_model=SImagePresignOut)
async def presign_image_upload(payload: SImagePresignIn, user_data: UserDepends):
    return await ImageBusinessService().presign(payload=payload)
