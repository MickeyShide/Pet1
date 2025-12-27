import pytest
from sqlalchemy.exc import IntegrityError

from app.models.feature import Feature, FeatureType
from tests.fixtures.factories import create_location, create_room


@pytest.mark.asyncio
async def test__feature_room_type_allows_only_room_id(db_session, faker):
    # Given
    location = await create_location(db_session, faker)
    room = await create_room(db_session, faker, location=location)
    feature = Feature(name="Projector", type=FeatureType.ROOM, room_id=room.id)

    # When
    db_session.add(feature)
    await db_session.commit()

    # Then
    assert feature.id is not None


@pytest.mark.asyncio
async def test__feature_location_type_allows_only_location_id(db_session, faker):
    # Given
    location = await create_location(db_session, faker)
    feature = Feature(name="Parking", type=FeatureType.LOCATION, location_id=location.id)

    # When
    db_session.add(feature)
    await db_session.commit()

    # Then
    assert feature.id is not None


@pytest.mark.asyncio
async def test__feature_room_type_rejects_location_id(db_session, faker):
    # Given
    location = await create_location(db_session, faker)
    feature = Feature(name="WiFi", type=FeatureType.ROOM, location_id=location.id)

    # When / Then
    db_session.add(feature)
    with pytest.raises(IntegrityError):
        await db_session.commit()
    await db_session.rollback()


@pytest.mark.asyncio
async def test__feature_location_type_rejects_room_id(db_session, faker):
    # Given
    location = await create_location(db_session, faker)
    room = await create_room(db_session, faker, location=location)
    feature = Feature(name="Stage", type=FeatureType.LOCATION, room_id=room.id)

    # When / Then
    db_session.add(feature)
    with pytest.raises(IntegrityError):
        await db_session.commit()
    await db_session.rollback()


@pytest.mark.asyncio
async def test__feature_room_type_rejects_missing_room_id(db_session):
    # Given
    feature = Feature(name="No target", type=FeatureType.ROOM)

    # When / Then
    db_session.add(feature)
    with pytest.raises(IntegrityError):
        await db_session.commit()
    await db_session.rollback()


@pytest.mark.asyncio
async def test__feature_location_type_rejects_missing_location_id(db_session):
    # Given
    feature = Feature(name="No target", type=FeatureType.LOCATION)

    # When / Then
    db_session.add(feature)
    with pytest.raises(IntegrityError):
        await db_session.commit()
    await db_session.rollback()


@pytest.mark.asyncio
async def test__feature_rejects_both_targets(db_session, faker):
    # Given
    location = await create_location(db_session, faker)
    room = await create_room(db_session, faker, location=location)
    feature = Feature(
        name="Conflicting",
        type=FeatureType.ROOM,
        room_id=room.id,
        location_id=location.id,
    )

    # When / Then
    db_session.add(feature)
    with pytest.raises(IntegrityError):
        await db_session.commit()
    await db_session.rollback()
