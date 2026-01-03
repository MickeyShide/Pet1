import pytest
from sqlalchemy import select

from app.api import deps
from app.models import Feature
from app.models.feature import FeatureType
from app.schemas.auth import SAccessToken
from app.utils.err.base.forbidden import ForbiddenException
from tests.fixtures.factories import create_feature, create_location, create_room


def override_token(app, *, admin: bool):
    async def fake_dep(jwt_token: deps.HTTPBearerDepends):
        return SAccessToken(sub="1", admin=admin)

    async def fake_admin_dep(jwt_token: deps.HTTPBearerDepends):
        if admin:
            return SAccessToken(sub="1", admin=True)
        raise ForbiddenException("Admin required")

    app.dependency_overrides[deps.get_token_data] = fake_dep
    app.dependency_overrides[deps.get_admin_token_data] = fake_admin_dep


def auth_header():
    return {"Authorization": "Bearer stub"}


@pytest.mark.asyncio
async def test__get_all_features_returns_empty(async_client):
    response = await async_client.get("/features")

    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test__get_all_features_returns_features(async_client, db_session, faker):
    location = await create_location(db_session, faker)
    room = await create_room(db_session, faker, location=location)
    feature_room = await create_feature(db_session, faker, room=room, name="Projector")
    feature_location = await create_feature(db_session, faker, location=location, name="Parking")
    await db_session.commit()

    response = await async_client.get("/features")

    assert response.status_code == 200, response.text
    payload = response.json()
    ids = {item["id"] for item in payload}
    assert {feature_room.id, feature_location.id}.issubset(ids)


@pytest.mark.asyncio
async def test__get_feature_by_id_returns_feature(async_client, db_session, faker):
    location = await create_location(db_session, faker)
    room = await create_room(db_session, faker, location=location)
    feature = await create_feature(db_session, faker, room=room, name="Screen")
    await db_session.commit()

    response = await async_client.get(f"/features/{feature.id}")

    assert response.status_code == 200, response.text
    data = response.json()
    assert data["id"] == feature.id
    assert data["name"] == "Screen"
    assert data["type"] == FeatureType.ROOM.value


@pytest.mark.asyncio
async def test__get_feature_by_id_not_found(async_client):
    response = await async_client.get("/features/99999")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test__create_feature_requires_admin(async_client, db_session, faker):
    location = await create_location(db_session, faker)
    room = await create_room(db_session, faker, location=location)
    await db_session.commit()
    override_token(async_client.app_ref, admin=False)

    response = await async_client.post(
        "/features",
        json={"name": "Projector", "type": "ROOM", "room_id": room.id},
        headers=auth_header(),
    )

    async_client.app_ref.dependency_overrides.clear()
    assert response.status_code == 403


@pytest.mark.asyncio
async def test__create_feature_with_admin(async_client, db_session, faker):
    location = await create_location(db_session, faker)
    room = await create_room(db_session, faker, location=location)
    await db_session.commit()
    override_token(async_client.app_ref, admin=True)

    response = await async_client.post(
        "/features",
        json={"name": "Projector", "type": "ROOM", "room_id": room.id},
        headers=auth_header(),
    )

    async_client.app_ref.dependency_overrides.clear()
    assert response.status_code == 200, response.text
    created_id = response.json()["id"]
    stored = await db_session.get(Feature, created_id)
    assert stored is not None
    assert stored.room_id == room.id


@pytest.mark.asyncio
async def test__create_location_feature_with_admin(async_client, db_session, faker):
    location = await create_location(db_session, faker)
    await db_session.commit()
    override_token(async_client.app_ref, admin=True)

    response = await async_client.post(
        "/features",
        json={"name": "Parking", "type": "LOCATION", "location_id": location.id},
        headers=auth_header(),
    )

    async_client.app_ref.dependency_overrides.clear()
    assert response.status_code == 200, response.text
    created_id = response.json()["id"]
    stored = await db_session.get(Feature, created_id)
    assert stored is not None
    assert stored.location_id == location.id
    assert stored.room_id is None


@pytest.mark.asyncio
async def test__create_feature_invalid_payload_returns_422(async_client, db_session, faker):
    override_token(async_client.app_ref, admin=True)

    response = await async_client.post(
        "/features",
        json={"name": "Bad", "type": "ROOM"},
        headers=auth_header(),
    )

    async_client.app_ref.dependency_overrides.clear()
    assert response.status_code == 422, response.text


@pytest.mark.asyncio
async def test__update_feature_requires_admin(async_client, db_session, faker):
    location = await create_location(db_session, faker)
    room = await create_room(db_session, faker, location=location)
    feature = await create_feature(db_session, faker, room=room, name="Old")
    await db_session.commit()
    override_token(async_client.app_ref, admin=False)

    response = await async_client.patch(
        f"/features/{feature.id}",
        json={"name": "New"},
        headers=auth_header(),
    )

    async_client.app_ref.dependency_overrides.clear()
    assert response.status_code == 403


@pytest.mark.asyncio
async def test__update_feature_with_admin(async_client, db_session, faker):
    location = await create_location(db_session, faker)
    room = await create_room(db_session, faker, location=location)
    feature = await create_feature(db_session, faker, room=room, name="Old")
    await db_session.commit()
    override_token(async_client.app_ref, admin=True)

    response = await async_client.patch(
        f"/features/{feature.id}",
        json={"name": "New"},
        headers=auth_header(),
    )

    async_client.app_ref.dependency_overrides.clear()
    assert response.status_code == 200, response.text
    await db_session.refresh(feature)
    assert feature.name == "New"


@pytest.mark.asyncio
async def test__update_feature_switches_to_location(async_client, db_session, faker):
    location = await create_location(db_session, faker)
    other_location = await create_location(db_session, faker)
    room = await create_room(db_session, faker, location=location)
    feature = await create_feature(db_session, faker, room=room, name="Old")
    await db_session.commit()
    override_token(async_client.app_ref, admin=True)

    response = await async_client.patch(
        f"/features/{feature.id}",
        json={"type": "LOCATION", "location_id": other_location.id, "room_id": None},
        headers=auth_header(),
    )

    async_client.app_ref.dependency_overrides.clear()
    assert response.status_code == 200, response.text
    await db_session.refresh(feature)
    assert feature.type == FeatureType.LOCATION
    assert feature.location_id == other_location.id
    assert feature.room_id is None


@pytest.mark.asyncio
async def test__update_feature_switches_to_room(async_client, db_session, faker):
    location = await create_location(db_session, faker)
    room = await create_room(db_session, faker, location=location)
    feature = await create_feature(db_session, faker, location=location, name="Old")
    await db_session.commit()
    override_token(async_client.app_ref, admin=True)

    response = await async_client.patch(
        f"/features/{feature.id}",
        json={"type": "ROOM", "room_id": room.id, "location_id": None},
        headers=auth_header(),
    )

    async_client.app_ref.dependency_overrides.clear()
    assert response.status_code == 200, response.text
    await db_session.refresh(feature)
    assert feature.type == FeatureType.ROOM
    assert feature.room_id == room.id
    assert feature.location_id is None


@pytest.mark.asyncio
async def test__update_feature_invalid_payload_returns_422(async_client, db_session, faker):
    location = await create_location(db_session, faker)
    room = await create_room(db_session, faker, location=location)
    feature = await create_feature(db_session, faker, room=room, name="Old")
    await db_session.commit()
    override_token(async_client.app_ref, admin=True)

    response = await async_client.patch(
        f"/features/{feature.id}",
        json={"room_id": room.id, "location_id": location.id},
        headers=auth_header(),
    )

    async_client.app_ref.dependency_overrides.clear()
    assert response.status_code == 422, response.text


@pytest.mark.asyncio
async def test__update_feature_type_without_target_returns_422(async_client, db_session, faker):
    location = await create_location(db_session, faker)
    room = await create_room(db_session, faker, location=location)
    feature = await create_feature(db_session, faker, room=room, name="Old")
    await db_session.commit()
    override_token(async_client.app_ref, admin=True)

    response = await async_client.patch(
        f"/features/{feature.id}",
        json={"type": "LOCATION"},
        headers=auth_header(),
    )

    async_client.app_ref.dependency_overrides.clear()
    assert response.status_code == 422, response.text


@pytest.mark.asyncio
async def test__update_feature_room_id_on_location_returns_422(async_client, db_session, faker):
    location = await create_location(db_session, faker)
    room = await create_room(db_session, faker, location=location)
    feature = await create_feature(db_session, faker, location=location, name="Old")
    await db_session.commit()
    override_token(async_client.app_ref, admin=True)

    response = await async_client.patch(
        f"/features/{feature.id}",
        json={"room_id": room.id},
        headers=auth_header(),
    )

    async_client.app_ref.dependency_overrides.clear()
    assert response.status_code == 422, response.text


@pytest.mark.asyncio
async def test__update_feature_empty_payload_returns_422(async_client, db_session, faker):
    location = await create_location(db_session, faker)
    room = await create_room(db_session, faker, location=location)
    feature = await create_feature(db_session, faker, room=room, name="Old")
    await db_session.commit()
    override_token(async_client.app_ref, admin=True)

    response = await async_client.patch(
        f"/features/{feature.id}",
        json={},
        headers=auth_header(),
    )

    async_client.app_ref.dependency_overrides.clear()
    assert response.status_code == 422, response.text


@pytest.mark.asyncio
async def test__update_feature_not_found(async_client):
    override_token(async_client.app_ref, admin=True)

    response = await async_client.patch(
        "/features/9999",
        json={"name": "Missing"},
        headers=auth_header(),
    )

    async_client.app_ref.dependency_overrides.clear()
    assert response.status_code == 404


@pytest.mark.asyncio
async def test__delete_feature_requires_admin(async_client, db_session, faker):
    location = await create_location(db_session, faker)
    room = await create_room(db_session, faker, location=location)
    feature = await create_feature(db_session, faker, room=room, name="Old")
    await db_session.commit()
    override_token(async_client.app_ref, admin=False)

    response = await async_client.delete(
        f"/features/{feature.id}",
        headers=auth_header(),
    )

    async_client.app_ref.dependency_overrides.clear()
    assert response.status_code == 403


@pytest.mark.asyncio
async def test__delete_feature_with_admin(async_client, db_session, faker):
    location = await create_location(db_session, faker)
    room = await create_room(db_session, faker, location=location)
    feature = await create_feature(db_session, faker, room=room, name="Old")
    await db_session.commit()
    override_token(async_client.app_ref, admin=True)

    response = await async_client.delete(
        f"/features/{feature.id}",
        headers=auth_header(),
    )

    async_client.app_ref.dependency_overrides.clear()
    assert response.status_code == 204
    result = await db_session.execute(select(Feature.id).where(Feature.id == feature.id))
    assert result.scalar_one_or_none() is None


@pytest.mark.asyncio
async def test__delete_feature_not_found(async_client):
    override_token(async_client.app_ref, admin=True)

    response = await async_client.delete(
        "/features/9999",
        headers=auth_header(),
    )

    async_client.app_ref.dependency_overrides.clear()
    assert response.status_code == 404
