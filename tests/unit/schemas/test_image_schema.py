import pytest
from pydantic import ValidationError

from app.models.image import ImageType
from app.schemas.image import SImageOut, SImageUploadIn, SImagePresignOut


def test__image_out_allows_null_image2x():
    data = SImageOut(
        id=1,
        image1x="images/room/1.jpg",
        image2x=None,
        type=ImageType.ROOM,
        file_id=10,
    )

    assert data.image2x is None


def test__image_out_rejects_extra_fields():
    with pytest.raises(ValidationError):
        SImageOut(
            id=1,
            image1x="images/room/1.jpg",
            image2x=None,
            type=ImageType.ROOM,
            file_id=10,
            extra_field="nope",
        )


def test__image_upload_in_requires_fields():
    with pytest.raises(ValidationError):
        SImageUploadIn(mime="image/jpeg")


def test__image_upload_in_rejects_extra_fields():
    with pytest.raises(ValidationError):
        SImageUploadIn(
            mime="image/jpeg",
            ext="jpg",
            size=123,
            original_name="a.jpg",
            extra="nope",
        )


def test__image_upload_in_allows_null_original_name():
    data = SImageUploadIn(mime="image/png", ext="png", size=123, original_name=None)
    assert data.original_name is None


def test__image_out_requires_file_id():
    with pytest.raises(ValidationError):
        SImageOut(id=1, image1x="images/room/1.jpg", image2x=None, type=ImageType.ROOM)


def test__image_presign_out_rejects_extra_fields():
    with pytest.raises(ValidationError):
        SImagePresignOut(
            id=1,
            upload_url="http://s3.local/upload",
            public_url="http://cdn.local/public.png",
            extra="nope",
        )


def test__image_presign_out_requires_urls():
    with pytest.raises(ValidationError):
        SImagePresignOut(id=1)
