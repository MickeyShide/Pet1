from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy.exc import IntegrityError, NoResultFound

from app.repositories.payment import PaymentRepository
from tests.fixtures.factories import (
    create_booking,
    create_location,
    create_room,
    create_timeslot,
    create_user,
)


@pytest.mark.asyncio
async def test__payment_repo__create_payment_once_per_booking(db_session, faker):
    # Given
    user = await create_user(db_session, faker)
    location = await create_location(db_session, faker)
    room = await create_room(db_session, faker, location=location)
    start = faker.date_time_this_month(tzinfo=timezone.utc)
    slot = await create_timeslot(
        db_session,
        room=room,
        start_datetime=start,
        end_datetime=start + timedelta(hours=1),
    )
    booking = await create_booking(db_session, user=user, room=room, timeslot=slot)
    repo = PaymentRepository(db_session)

    # When
    payment = await repo.create(booking_id=booking.id, external_id="ext-1")

    # Then
    assert payment.booking_id == booking.id
    assert payment.external_id == "ext-1"

    # And duplicate booking_id violates unique constraint
    with pytest.raises(IntegrityError):
        await repo.create(booking_id=booking.id, external_id="ext-dup")


@pytest.mark.asyncio
async def test__payment_repo__get_by_id_not_found(db_session):
    repo = PaymentRepository(db_session)
    with pytest.raises(NoResultFound):
        await repo.get_first(id=9999)
