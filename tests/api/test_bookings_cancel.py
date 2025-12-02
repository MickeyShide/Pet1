from datetime import datetime, timedelta, timezone

import pytest

from app.api import deps
from app.models import Booking
from app.models.booking import BookingStatus
from app.schemas.auth import SAccessToken
from tests.fixtures.factories import (
    create_booking,
    create_location,
    create_room,
    create_timeslot,
    create_user,
)


def override_token(app, token: SAccessToken):
    async def fake_dep(jwt_token: deps.HTTPBearerDepends):
        return token

    app.dependency_overrides[deps.get_token_data] = fake_dep
    app.dependency_overrides[deps.get_admin_token_data] = fake_dep


@pytest.mark.asyncio
async def test__cancel_booking_endpoint__requires_auth(async_client):
    response = await async_client.post("/bookings/1/cancel")
    # ❗BUG FOUND: endpoint responds 403 from HTTPBearer instead of expected 401 for missing auth.
    assert response.status_code == 401


@pytest.mark.asyncio
async def test__cancel_booking_endpoint__owner_can_cancel_pending(async_client, db_session, faker):
    user = await create_user(db_session, faker)
    token = SAccessToken(sub=str(user.id), admin=False)
    override_token(async_client.app_ref, token)
    location = await create_location(db_session, faker)
    room = await create_room(db_session, faker, location=location)
    slot = await create_timeslot(
        db_session,
        room=room,
        start_datetime=datetime.now(timezone.utc),
        end_datetime=datetime.now(timezone.utc) + timedelta(hours=1),
    )
    booking = await create_booking(
        db_session,
        user=user,
        room=room,
        timeslot=slot,
        status=BookingStatus.PENDING_PAYMENTS,
    )
    await db_session.commit()

    response = await async_client.post(
        f"/bookings/{booking.id}/cancel",
        headers={"Authorization": "Bearer test"},
    )

    async_client.app_ref.dependency_overrides.clear()
    assert response.status_code == 200, response.text
    assert response.json() is True


@pytest.mark.asyncio
async def test__cancel_booking_endpoint__returns_not_found_for_other_user(async_client, db_session, faker):
    owner = await create_user(db_session, faker)
    other = await create_user(db_session, faker)
    token = SAccessToken(sub=str(other.id), admin=False)
    override_token(async_client.app_ref, token)
    location = await create_location(db_session, faker)
    room = await create_room(db_session, faker, location=location)
    slot = await create_timeslot(
        db_session,
        room=room,
        start_datetime=datetime.now(timezone.utc),
        end_datetime=datetime.now(timezone.utc) + timedelta(hours=1),
    )
    booking = await create_booking(
        db_session,
        user=owner,
        room=room,
        timeslot=slot,
        status=BookingStatus.PENDING_PAYMENTS,
    )
    await db_session.commit()

    response = await async_client.post(
        f"/bookings/{booking.id}/cancel",
        headers={"Authorization": "Bearer test"},
    )

    async_client.app_ref.dependency_overrides.clear()
    assert response.status_code == 404


@pytest.mark.asyncio
async def test__cancel_booking_endpoint__admin_can_cancel_others(async_client, db_session, faker):
    admin = await create_user(db_session, faker)
    token = SAccessToken(sub=str(admin.id), admin=True)
    override_token(async_client.app_ref, token)
    location = await create_location(db_session, faker)
    room = await create_room(db_session, faker, location=location)
    slot = await create_timeslot(
        db_session,
        room=room,
        start_datetime=datetime.now(timezone.utc),
        end_datetime=datetime.now(timezone.utc) + timedelta(hours=1),
    )
    booking_user = await create_user(db_session, faker)
    booking = await create_booking(
        db_session,
        user=booking_user,
        room=room,
        timeslot=slot,
        status=BookingStatus.PENDING_PAYMENTS,
    )
    await db_session.commit()

    response = await async_client.post(
        f"/bookings/{booking.id}/cancel",
        headers={"Authorization": "Bearer test"},
    )

    async_client.app_ref.dependency_overrides.clear()
    assert response.status_code == 200, response.text
    assert response.json() is True


@pytest.mark.asyncio
async def test__cancel_booking_endpoint__not_found(async_client, db_session, faker):
    user = await create_user(db_session, faker)
    token = SAccessToken(sub=str(user.id), admin=False)
    override_token(async_client.app_ref, token)
    await db_session.commit()

    response = await async_client.post(
        "/bookings/9999/cancel",
        headers={"Authorization": "Bearer test"},
    )

    async_client.app_ref.dependency_overrides.clear()
    assert response.status_code == 404


@pytest.mark.asyncio
async def test__cancel_booking_endpoint__conflict_when_not_pending(async_client, db_session, faker):
    user = await create_user(db_session, faker)
    token = SAccessToken(sub=str(user.id), admin=False)
    override_token(async_client.app_ref, token)
    location = await create_location(db_session, faker)
    room = await create_room(db_session, faker, location=location)
    slot = await create_timeslot(
        db_session,
        room=room,
        start_datetime=datetime.now(timezone.utc),
        end_datetime=datetime.now(timezone.utc) + timedelta(hours=1),
    )
    booking = await create_booking(
        db_session,
        user=user,
        room=room,
        timeslot=slot,
        status=BookingStatus.PAID,
    )
    await db_session.commit()

    response = await async_client.post(
        f"/bookings/{booking.id}/cancel",
        headers={"Authorization": "Bearer test"},
    )

    async_client.app_ref.dependency_overrides.clear()
    assert response.status_code == 409


@pytest.mark.asyncio
async def test__cancel_booking_endpoint__allows_rebooking_same_slot(async_client, db_session, faker):
    user = await create_user(db_session, faker)
    token = SAccessToken(sub=str(user.id), admin=False)
    override_token(async_client.app_ref, token)
    location = await create_location(db_session, faker)
    room = await create_room(db_session, faker, location=location)
    slot = await create_timeslot(
        db_session,
        room=room,
        start_datetime=datetime.now(timezone.utc),
        end_datetime=datetime.now(timezone.utc) + timedelta(hours=1),
    )
    booking = await create_booking(
        db_session,
        user=user,
        room=room,
        timeslot=slot,
        status=BookingStatus.PENDING_PAYMENTS,
    )
    await db_session.commit()

    cancel_response = await async_client.post(
        f"/bookings/{booking.id}/cancel",
        headers={"Authorization": "Bearer test"},
    )
    assert cancel_response.status_code == 200, cancel_response.text
    await db_session.refresh(booking)
    assert booking.status == BookingStatus.CANCELED

    rebook_response = await async_client.post(
        "/bookings/",
        json={"timeslot_id": slot.id},
        headers={"Authorization": "Bearer test"},
    )

    async_client.app_ref.dependency_overrides.clear()
    # ❗BUG FOUND: After cancellation the slot still fails the unique constraint (SQLite ignores the partial index), so rebooking currently crashes.
    assert rebook_response.status_code == 201, rebook_response.text
    new_booking_id = rebook_response.json()["id"]
    assert new_booking_id != booking.id
    stored_booking = await db_session.get(Booking, new_booking_id)
    assert stored_booking is not None
    assert stored_booking.timeslot_id == slot.id


@pytest.mark.asyncio
async def test__cancel_booking_endpoint__sets_canceled_at(async_client, db_session, faker):
    user = await create_user(db_session, faker)
    token = SAccessToken(sub=str(user.id), admin=False)
    override_token(async_client.app_ref, token)
    location = await create_location(db_session, faker)
    room = await create_room(db_session, faker, location=location)
    slot = await create_timeslot(
        db_session,
        room=room,
        start_datetime=datetime.now(timezone.utc),
        end_datetime=datetime.now(timezone.utc) + timedelta(hours=1),
    )
    booking = await create_booking(
        db_session,
        user=user,
        room=room,
        timeslot=slot,
        status=BookingStatus.PENDING_PAYMENTS,
    )
    await db_session.commit()

    response = await async_client.post(
        f"/bookings/{booking.id}/cancel",
        headers={"Authorization": "Bearer test"},
    )

    async_client.app_ref.dependency_overrides.clear()
    assert response.status_code == 200, response.text
    await db_session.refresh(booking)
    assert booking.status == BookingStatus.CANCELED
    assert booking.canceled_at is not None


@pytest.mark.asyncio
async def test__cancel_booking_endpoint__owner_cancel_already_canceled(async_client, db_session, faker):
    user = await create_user(db_session, faker)
    token = SAccessToken(sub=str(user.id), admin=False)
    override_token(async_client.app_ref, token)
    location = await create_location(db_session, faker)
    room = await create_room(db_session, faker, location=location)
    slot = await create_timeslot(
        db_session,
        room=room,
        start_datetime=datetime.now(timezone.utc),
        end_datetime=datetime.now(timezone.utc) + timedelta(hours=1),
    )
    booking = await create_booking(
        db_session,
        user=user,
        room=room,
        timeslot=slot,
        status=BookingStatus.CANCELED,
    )
    await db_session.commit()

    response = await async_client.post(
        f"/bookings/{booking.id}/cancel",
        headers={"Authorization": "Bearer test"},
    )

    async_client.app_ref.dependency_overrides.clear()
    assert response.status_code == 409


@pytest.mark.asyncio
async def test__cancel_booking_endpoint__admin_cancel_already_canceled(async_client, db_session, faker):
    admin = await create_user(db_session, faker)
    token = SAccessToken(sub=str(admin.id), admin=True)
    override_token(async_client.app_ref, token)
    location = await create_location(db_session, faker)
    room = await create_room(db_session, faker, location=location)
    slot = await create_timeslot(
        db_session,
        room=room,
        start_datetime=datetime.now(timezone.utc),
        end_datetime=datetime.now(timezone.utc) + timedelta(hours=1),
    )
    owner = await create_user(db_session, faker)
    booking = await create_booking(
        db_session,
        user=owner,
        room=room,
        timeslot=slot,
        status=BookingStatus.CANCELED,
    )
    await db_session.commit()

    response = await async_client.post(
        f"/bookings/{booking.id}/cancel",
        headers={"Authorization": "Bearer test"},
    )

    async_client.app_ref.dependency_overrides.clear()
    assert response.status_code == 409


@pytest.mark.asyncio
async def test__cancel_booking_endpoint__admin_cancel_paid_booking(async_client, db_session, faker):
    admin = await create_user(db_session, faker)
    token = SAccessToken(sub=str(admin.id), admin=True)
    override_token(async_client.app_ref, token)
    location = await create_location(db_session, faker)
    room = await create_room(db_session, faker, location=location)
    slot = await create_timeslot(
        db_session,
        room=room,
        start_datetime=datetime.now(timezone.utc),
        end_datetime=datetime.now(timezone.utc) + timedelta(hours=1),
    )
    owner = await create_user(db_session, faker)
    booking = await create_booking(
        db_session,
        user=owner,
        room=room,
        timeslot=slot,
        status=BookingStatus.PAID,
    )
    await db_session.commit()

    response = await async_client.post(
        f"/bookings/{booking.id}/cancel",
        headers={"Authorization": "Bearer test"},
    )

    async_client.app_ref.dependency_overrides.clear()
    assert response.status_code == 409
