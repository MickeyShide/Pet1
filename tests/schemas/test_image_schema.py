import pytest
from pydantic import ValidationError

from app.models.image import ImageType
from app.schemas.image import SImageOut, SImagePresignIn


def test__image_out_allows_null_image2x():
    data = SImageOut(id=1, image1x="images/room/1.jpg", image2x=None, type=ImageType.ROOM)

    assert data.image2x is None


def test__image_out_rejects_extra_fields():
    with pytest.raises(ValidationError):
        SImageOut(
            id=1,
            image1x="images/room/1.jpg",
            image2x=None,
            type=ImageType.ROOM,
            extra_field="nope",
        )


def test__image_presign_in_requires_fields():
    with pytest.raises(ValidationError):
        SImagePresignIn(type=ImageType.ROOM, mime="image/jpeg")
