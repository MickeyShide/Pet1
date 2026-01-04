import pytest
from sqlalchemy.exc import IntegrityError

from app.models import Room
from tests.fixtures.factories import create_location


@pytest.mark.asyncio
async def test__room_rejects_non_positive_min_duration(db_session, faker):
    # Given
    location = await create_location(db_session, faker)
    room = Room(
        location_id=location.id,
        name="Bad min duration",
        capacity=1,
        description="invalid",
        is_active=True,
        hour_price=10,
        min_booking_duration_minutes=0,
        booking_step_minutes=15,
    )

    # When / Then
    db_session.add(room)
    with pytest.raises(IntegrityError):
        await db_session.commit()
    await db_session.rollback()


@pytest.mark.asyncio
async def test__room_rejects_non_positive_booking_step(db_session, faker):
    # Given
    location = await create_location(db_session, faker)
    room = Room(
        location_id=location.id,
        name="Bad step",
        capacity=1,
        description="invalid",
        is_active=True,
        hour_price=10,
        min_booking_duration_minutes=60,
        booking_step_minutes=0,
    )

    # When / Then
    db_session.add(room)
    with pytest.raises(IntegrityError):
        await db_session.commit()
    await db_session.rollback()


@pytest.mark.asyncio
async def test__room_rejects_step_gt_min_duration(db_session, faker):
    # Given
    location = await create_location(db_session, faker)
    room = Room(
        location_id=location.id,
        name="Step too large",
        capacity=1,
        description="invalid",
        is_active=True,
        hour_price=10,
        min_booking_duration_minutes=30,
        booking_step_minutes=60,
    )

    # When / Then
    db_session.add(room)
    with pytest.raises(IntegrityError):
        await db_session.commit()
    await db_session.rollback()
