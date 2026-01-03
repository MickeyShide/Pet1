import pytest
from sqlalchemy import select

from app.models import Feature
from app.models.feature import FeatureType
from app.schemas.feature import SFeatureCreate, SFeatureUpdate
from app.services.business.features import FeatureBusinessService
from tests.fixtures.factories import create_feature, create_location, create_room


@pytest.mark.asyncio
async def test__feature_business_service_get_all_returns_features(db_session, faker):
    location = await create_location(db_session, faker)
    room = await create_room(db_session, faker, location=location)
    feature_room = await create_feature(db_session, faker, room=room, name="Projector")
    feature_location = await create_feature(db_session, faker, location=location, name="Parking")
    await db_session.commit()
    service = FeatureBusinessService()

    result = await service.get_all()

    ids = {item.id for item in result}
    assert {feature_room.id, feature_location.id}.issubset(ids)


@pytest.mark.asyncio
async def test__feature_business_service_get_by_id_returns_feature(db_session, faker):
    location = await create_location(db_session, faker)
    room = await create_room(db_session, faker, location=location)
    feature = await create_feature(db_session, faker, room=room, name="Screen")
    await db_session.commit()
    service = FeatureBusinessService()

    result = await service.get_by_id(feature.id)

    assert result.id == feature.id
    assert result.name == "Screen"
    assert result.type == FeatureType.ROOM


@pytest.mark.asyncio
async def test__feature_business_service_create_persists_feature(db_session, faker):
    location = await create_location(db_session, faker)
    room = await create_room(db_session, faker, location=location)
    await db_session.commit()
    service = FeatureBusinessService()

    payload = SFeatureCreate(name="Projector", type=FeatureType.ROOM, room_id=room.id)
    result = await service.create(payload)

    assert result.id is not None
    stored = await db_session.get(Feature, result.id)
    assert stored is not None
    assert stored.room_id == room.id


@pytest.mark.asyncio
async def test__feature_business_service_update_changes_name(db_session, faker):
    location = await create_location(db_session, faker)
    room = await create_room(db_session, faker, location=location)
    feature = await create_feature(db_session, faker, room=room, name="Old")
    await db_session.commit()
    service = FeatureBusinessService()

    result = await service.update_by_id(feature.id, SFeatureUpdate(name="New"))

    assert result.name == "New"
    await db_session.refresh(feature)
    assert feature.name == "New"


@pytest.mark.asyncio
async def test__feature_business_service_delete_removes_feature(db_session, faker):
    location = await create_location(db_session, faker)
    room = await create_room(db_session, faker, location=location)
    feature = await create_feature(db_session, faker, room=room, name="Old")
    await db_session.commit()
    service = FeatureBusinessService()

    await service.delete_by_id(feature.id)

    stmt = select(Feature.id).where(Feature.id == feature.id)
    remaining = (await db_session.execute(stmt)).scalar_one_or_none()
    assert remaining is None
