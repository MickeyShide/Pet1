import pytest
from sqlalchemy.exc import IntegrityError

from tests.factories import create_location, create_room


@pytest.mark.asyncio
async def test__room_rejects_non_positive_min_duration(db_session, faker):
    # Given
    location = await create_location(db_session, faker)
    with pytest.raises(IntegrityError):
        await create_room(
            db_session,
            faker,
            location=location,
            min_booking_duration_minutes=0,
            booking_step_minutes=15,
        )
    await db_session.rollback()


@pytest.mark.asyncio
async def test__room_rejects_non_positive_booking_step(db_session, faker):
    # Given
    location = await create_location(db_session, faker)
    with pytest.raises(IntegrityError):
        await create_room(
            db_session,
            faker,
            location=location,
            min_booking_duration_minutes=60,
            booking_step_minutes=0,
        )
    await db_session.rollback()


@pytest.mark.asyncio
async def test__room_rejects_step_gt_min_duration(db_session, faker):
    # Given
    location = await create_location(db_session, faker)
    with pytest.raises(IntegrityError):
        await create_room(
            db_session,
            faker,
            location=location,
            min_booking_duration_minutes=30,
            booking_step_minutes=60,
        )
    await db_session.rollback()
