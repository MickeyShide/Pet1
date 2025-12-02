from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select

from app.models import TimeSlot
from app.schemas.timeslot import STimeSlotUpdate
from app.services.business.timeslots import TimeSlotBusinessService
from tests.fixtures.factories import (
    create_location,
    create_room,
    create_timeslot,
)


@pytest.mark.asyncio
async def test__update_timeslot_by_id__applies_partial_fields(db_session, faker):
    # Given
    location = await create_location(db_session, faker)
    room = await create_room(db_session, faker, location=location)
    start = datetime.now(timezone.utc)
    slot = await create_timeslot(
        db_session,
        room=room,
        start_datetime=start,
        end_datetime=start + timedelta(hours=1),
        base_price=200,
    )
    await db_session.commit()
    service = TimeSlotBusinessService()
    payload = STimeSlotUpdate(base_price=350)

    # When
    updated = await service.update_timeslot_by_id(slot.id, payload)

    # Then
    assert isinstance(updated, TimeSlot)
    assert updated.base_price == payload.base_price
    await db_session.refresh(slot)
    assert slot.base_price == payload.base_price


@pytest.mark.asyncio
async def test__delete_timeslot_by_id__removes_slot(db_session, faker):
    # Given
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
    service = TimeSlotBusinessService()

    # When
    await service.delete_timeslot_by_id(slot.id)

    # Then
    result = (await db_session.execute(select(TimeSlot).where(TimeSlot.id == slot.id))).scalar_one_or_none()
    assert result is None
