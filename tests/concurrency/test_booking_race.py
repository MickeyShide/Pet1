import asyncio
from datetime import datetime, timedelta, timezone

import pytest

from app.schemas.auth import SAccessToken
from app.schemas.booking import SBookingCreate
from app.services.business.bookings import BookingsBusinessService
from app.utils.err.booking import SlotAlreadyTaken
from tests.fixtures.factories import (
    create_location,
    create_room,
    create_timeslot,
    create_user,
)


@pytest.mark.asyncio
async def test__create_booking_concurrent_requests_only_one_succeeds(db_session, faker):
    user = await create_user(db_session, faker)
    location = await create_location(db_session, faker)
    room = await create_room(db_session, faker, location=location)
    start = datetime.now(timezone.utc)
    slot = await create_timeslot(
        db_session,
        room=room,
        start_datetime=start,
        end_datetime=start + timedelta(hours=1),
    )
    await db_session.commit()

    token = SAccessToken(sub=str(user.id), admin=False)
    start_event = asyncio.Event()

    async def _attempt():
        await start_event.wait()
        service = BookingsBusinessService(token_data=token)
        return await service.create_booking(SBookingCreate(timeslot_id=slot.id))

    task_a = asyncio.create_task(_attempt())
    task_b = asyncio.create_task(_attempt())
    start_event.set()

    results = await asyncio.gather(task_a, task_b, return_exceptions=True)
    successes = [item for item in results if not isinstance(item, Exception)]
    failures = [item for item in results if isinstance(item, Exception)]

    assert len(successes) == 1
    assert len(failures) == 1
    assert isinstance(failures[0], SlotAlreadyTaken)
