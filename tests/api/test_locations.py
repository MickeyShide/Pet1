from decimal import Decimal

import pytest
from sqlalchemy import select

from app.api import deps
from app.models.room import TimeSlotType
from app.schemas.auth import SAccessToken
from app.utils.err.base.forbidden import ForbiddenException
from app.models import Location, Room
from tests.fixtures.factories import (
    create_location,
    create_room,
)


def override_token(app, *, admin: bool):
    async def fake_get_token_data(jwt_token: deps.HTTPBearerDepends):
        return SAccessToken(sub="1", admin=admin)

    async def fake_admin_dep(jwt_token: deps.HTTPBearerDepends):
        if admin:
            return SAccessToken(sub="1", admin=True)
        raise ForbiddenException("Not allowed")

    app.dependency_overrides[deps.get_admin_token_data] = fake_admin_dep
    app.dependency_overrides[deps.get_token_data] = fake_get_token_data


@pytest.mark.asyncio
async def test__create_location_requires_admin(async_client, db_session, faker):
    override_token(async_client.app_ref, admin=False)
    payload = {
        "name": "HQ",
        "address": "1 Main",
        "description": "HQ office",
    }

    response = await async_client.post("/locations", json=payload, headers={"Authorization": "Bearer test"})

    async_client.app_ref.dependency_overrides.clear()
    assert response.status_code == 403, response.text


@pytest.mark.asyncio
async def test__create_location_with_admin(async_client, db_session, faker):
    override_token(async_client.app_ref, admin=True)
    payload = {
        "name": "HQ",
        "address": "1 Main",
        "description": "HQ office",
    }

    response = await async_client.post("/locations", json=payload, headers={"Authorization": "Bearer test"})

    async_client.app_ref.dependency_overrides.clear()
    assert response.status_code == 200, response.text
    stored = await db_session.execute(Location.__table__.select().where(Location.name == "HQ"))
    assert stored.first() is not None


@pytest.mark.asyncio
async def test__create_room_under_location(async_client, db_session, faker):
    location = await create_location(db_session, faker)
    override_token(async_client.app_ref, admin=True)
    payload = {
        "name": "Board",
        "capacity": 8,
        "description": "Board room",
        "is_active": True,
        "time_slot_type": TimeSlotType.FIXED.value,
        "hour_price": "12.5",
    }
    await db_session.commit()

    response = await async_client.post(
        f"/locations/{location.id}/rooms",
        json=payload,
        headers={"Authorization": "Bearer test"},
    )

    async_client.app_ref.dependency_overrides.clear()
    assert response.status_code == 200, response.text
    stored = await db_session.execute(Room.__table__.select().where(Room.location_id == location.id))
    assert stored.first() is not None


@pytest.mark.asyncio
async def test__create_room_under_location_requires_admin(async_client, db_session, faker):
    location = await create_location(db_session, faker)
    await db_session.commit()
    override_token(async_client.app_ref, admin=False)
    payload = {
        "name": "Board",
        "capacity": 8,
        "description": "Board room",
        "is_active": True,
    }

    response = await async_client.post(
        f"/locations/{location.id}/rooms",
        json=payload,
        headers={"Authorization": "Bearer test"},
    )

    async_client.app_ref.dependency_overrides.clear()
    assert response.status_code == 403


@pytest.mark.asyncio
async def test__get_all_locations_returns_all(async_client, db_session, faker):
    loc_a = await create_location(db_session, faker)
    loc_b = await create_location(db_session, faker)
    await db_session.commit()

    response = await async_client.get("/locations")

    assert response.status_code == 200
    names = {item["name"] for item in response.json()}
    assert {loc_a.name, loc_b.name}.issubset(names)


@pytest.mark.asyncio
async def test__get_location_by_id_returns_location(async_client, db_session, faker):
    loc = await create_location(db_session, faker)
    await db_session.commit()

    response = await async_client.get(f"/locations/{loc.id}")

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == loc.id
    assert data["name"] == loc.name


@pytest.mark.asyncio
async def test__get_location_by_id_not_found(async_client):
    response = await async_client.get("/locations/99999")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test__get_rooms_by_location_returns_rooms(async_client, db_session, faker):
    location = await create_location(db_session, faker)
    room_a = await create_room(db_session, faker, location=location)
    room_b = await create_room(db_session, faker, location=location)
    await db_session.commit()

    response = await async_client.get(f"/locations/{location.id}/rooms")

    assert response.status_code == 200
    ids = {room["id"] for room in response.json()}
    assert ids == {room_a.id, room_b.id}


@pytest.mark.asyncio
async def test__update_location_requires_admin__returns_forbidden(async_client, db_session, faker):
    # Given
    location = await create_location(db_session, faker)
    await db_session.commit()
    override_token(async_client.app_ref, admin=False)

    # When
    response = await async_client.patch(
        f"/locations/{location.id}",
        json={"name": "Updated"},
        headers={"Authorization": "Bearer test"},
    )

    async_client.app_ref.dependency_overrides.clear()
    # Then
    assert response.status_code == 403


@pytest.mark.asyncio
async def test__update_location_with_admin__updates_record(async_client, db_session, faker):
    # Given
    location = await create_location(db_session, faker)
    await db_session.commit()
    override_token(async_client.app_ref, admin=True)

    # When
    response = await async_client.patch(
        f"/locations/{location.id}",
        json={"name": "Renamed HQ"},
        headers={"Authorization": "Bearer test"},
    )

    async_client.app_ref.dependency_overrides.clear()
    # Then
    assert response.status_code == 200, response.text
    await db_session.refresh(location)
    assert location.name == "Renamed HQ"


@pytest.mark.asyncio
async def test__delete_location_requires_admin__returns_forbidden(async_client, db_session, faker):
    # Given
    location = await create_location(db_session, faker)
    await db_session.commit()
    override_token(async_client.app_ref, admin=False)

    # When
    response = await async_client.delete(
        f"/locations/{location.id}",
        headers={"Authorization": "Bearer test"},
    )

    async_client.app_ref.dependency_overrides.clear()
    # Then
    assert response.status_code == 403


@pytest.mark.asyncio
async def test__delete_location_with_admin__removes_record(async_client, db_session, faker):
    # Given
    location = await create_location(db_session, faker)
    await db_session.commit()
    override_token(async_client.app_ref, admin=True)

    # When
    response = await async_client.delete(
        f"/locations/{location.id}",
        headers={"Authorization": "Bearer test"},
    )

    async_client.app_ref.dependency_overrides.clear()
    # Then
    assert response.status_code == 204
    stmt = select(Location.id).where(Location.id == location.id)
    result = await db_session.execute(stmt)
    assert result.scalar_one_or_none() is None


@pytest.mark.asyncio
async def test__update_location_with_admin__not_found(async_client):
    override_token(async_client.app_ref, admin=True)

    response = await async_client.patch(
        "/locations/9999",
        json={"name": "Missing"},
        headers={"Authorization": "Bearer test"},
    )

    async_client.app_ref.dependency_overrides.clear()
    assert response.status_code == 404


@pytest.mark.asyncio
async def test__delete_location_with_admin__not_found(async_client):
    override_token(async_client.app_ref, admin=True)

    response = await async_client.delete(
        "/locations/9999",
        headers={"Authorization": "Bearer test"},
    )

    async_client.app_ref.dependency_overrides.clear()
    assert response.status_code == 404
