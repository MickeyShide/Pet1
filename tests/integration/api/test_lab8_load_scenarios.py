import asyncio
from datetime import datetime, timedelta, timezone

import pytest

from app.schemas.auth import SAccessToken
from tests.factories import create_location, create_room, create_timeslot, create_user
from tests.integration.api.helpers import clear_overrides, override_token


@pytest.mark.asyncio
@pytest.mark.concurrent_db
@pytest.mark.load
@pytest.mark.integration
async def test__concurrent_booking_requests__only_one_books_same_slot(async_client, db_session, faker):
    user = await create_user(db_session, faker)
    location = await create_location(db_session, faker)
    room = await create_room(db_session, faker, location=location)
    start = datetime.now(timezone.utc) + timedelta(hours=1)
    slot = await create_timeslot(
        db_session,
        room=room,
        start_datetime=start,
        end_datetime=start + timedelta(hours=1),
    )
    await db_session.commit()

    override_token(async_client.app_ref, SAccessToken(sub=str(user.id), admin=False))

    responses = await asyncio.gather(
        *[
            async_client.post(
                "/bookings",
                json={"timeslot_id": slot.id},
                headers={"Authorization": "Bearer test"},
            )
            for _ in range(6)
        ]
    )

    clear_overrides(async_client.app_ref)
    status_codes = [response.status_code for response in responses]

    assert status_codes.count(201) == 1
    assert status_codes.count(409) >= 1


@pytest.mark.asyncio
@pytest.mark.load
@pytest.mark.integration
async def test__readonly_endpoint__handles_small_concurrent_load(async_client):
    responses = await asyncio.gather(*[async_client.get("/features") for _ in range(20)])

    assert all(response.status_code == 200 for response in responses)
