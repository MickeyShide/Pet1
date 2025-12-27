import pytest

from app.models.image import Image, ImageType


@pytest.mark.asyncio
async def test__image_persists_with_room_type(db_session):
    # Given
    image = Image(image1x="/img/1x.png", image2x=None, type=ImageType.ROOM)

    # When
    db_session.add(image)
    await db_session.commit()

    # Then
    assert image.id is not None
    assert image.type == ImageType.ROOM


@pytest.mark.asyncio
async def test__image_allows_null_paths(db_session):
    # Given
    image = Image(image1x=None, image2x=None, type=ImageType.LOCATION)

    # When
    db_session.add(image)
    await db_session.commit()

    # Then
    assert image.id is not None
    assert image.image1x is None
    assert image.image2x is None
