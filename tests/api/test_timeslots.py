from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select

from app.api import deps
from app.schemas.auth import SAccessToken
from app.utils.err.base.forbidden import ForbiddenException
from app.models import TimeSlot
from tests.fixtures.factories import (
    create_location,
    create_room,
    create_timeslot,
)


def override_token(app, *, admin: bool):
    async def fake_token(jwt_token: deps.HTTPBearerDepends):
        return SAccessToken(sub="1", admin=admin)

    async def fake_admin(jwt_token: deps.HTTPBearerDepends):
        if admin:
            return SAccessToken(sub="1", admin=True)
        raise ForbiddenException("Admin required")

    app.dependency_overrides[deps.get_token_data] = fake_token
    app.dependency_overrides[deps.get_admin_token_data] = fake_admin


def auth_header():
    return {"Authorization": "Bearer stub"}


@pytest.mark.asyncio
async def test__update_timeslot_requires_admin(async_client, db_session, faker):
    location = await create_location(db_session, faker)
    room = await create_room(db_session, faker, location=location)
    slot = await create_timeslot(
        db_session,
        room=room,
        start_datetime=datetime.now(timezone.utc),
        end_datetime=datetime.now(timezone.utc) + timedelta(hours=1),
    )
    await db_session.commit()
    override_token(async_client.app_ref, admin=False)

    response = await async_client.patch(
        f"/timeslots/{slot.id}",
        json={"base_price": 500},
        headers=auth_header(),
    )

    async_client.app_ref.dependency_overrides.clear()
    assert response.status_code == 403


@pytest.mark.asyncio
async def test__update_timeslot_with_admin(async_client, db_session, faker):
    location = await create_location(db_session, faker)
    room = await create_room(db_session, faker, location=location)
    slot = await create_timeslot(
        db_session,
        room=room,
        start_datetime=datetime.now(timezone.utc),
        end_datetime=datetime.now(timezone.utc) + timedelta(hours=1),
        base_price=100,
    )
    await db_session.commit()
    override_token(async_client.app_ref, admin=True)

    response = await async_client.patch(
        f"/timeslots/{slot.id}",
        json={"base_price": 200},
        headers=auth_header(),
    )

    async_client.app_ref.dependency_overrides.clear()
    assert response.status_code == 200, response.text
    await db_session.refresh(slot)
    assert slot.base_price == 200


@pytest.mark.asyncio
async def test__delete_timeslot_requires_admin(async_client, db_session, faker):
    location = await create_location(db_session, faker)
    room = await create_room(db_session, faker, location=location)
    slot = await create_timeslot(
        db_session,
        room=room,
        start_datetime=datetime.now(timezone.utc),
        end_datetime=datetime.now(timezone.utc) + timedelta(hours=1),
    )
    await db_session.commit()
    override_token(async_client.app_ref, admin=False)

    slot_id = slot.id
    response = await async_client.delete(f"/timeslots/{slot_id}", headers=auth_header())

    async_client.app_ref.dependency_overrides.clear()
    assert response.status_code == 403


@pytest.mark.asyncio
async def test__delete_timeslot_with_admin(async_client, db_session, faker):
    location = await create_location(db_session, faker)
    room = await create_room(db_session, faker, location=location)
    slot = await create_timeslot(
        db_session,
        room=room,
        start_datetime=datetime.now(timezone.utc),
        end_datetime=datetime.now(timezone.utc) + timedelta(hours=1),
    )
    await db_session.commit()
    override_token(async_client.app_ref, admin=True)

    slot_id = slot.id
    response = await async_client.delete(f"/timeslots/{slot_id}", headers=auth_header())

    async_client.app_ref.dependency_overrides.clear()
    assert response.status_code == 204
    db_session.expire_all()
    result = await db_session.execute(
        select(TimeSlot).where(TimeSlot.id == slot_id)
    )
    remaining = result.scalar_one_or_none()
    assert remaining is None


@pytest.mark.asyncio
async def test__update_timeslot_not_found_returns_404(async_client):
    override_token(async_client.app_ref, admin=True)

    response = await async_client.patch(
        "/timeslots/9999",
        json={"base_price": 200},
        headers=auth_header(),
    )

    async_client.app_ref.dependency_overrides.clear()
    assert response.status_code == 404


@pytest.mark.asyncio
async def test__delete_timeslot_not_found_returns_404(async_client):
    override_token(async_client.app_ref, admin=True)

    response = await async_client.delete(
        "/timeslots/9999",
        headers=auth_header(),
    )

    async_client.app_ref.dependency_overrides.clear()
    assert response.status_code == 404
