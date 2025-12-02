from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Booking, Location, Room, TimeSlot, User
from app.models.booking import BookingStatus
from app.models.timeslot import TimeSlotStatus
from app.models.user import UserRole


async def create_user(
    session: AsyncSession,
    faker,
    *,
    role: UserRole = UserRole.USER,
) -> User:
    user = User(
        first_name=faker.first_name(),
        second_name=faker.last_name(),
        email=faker.unique.email(),
        username=faker.unique.user_name(),
        hashed_password=faker.sha256(raw_output=False),
        role=role,
    )
    session.add(user)
    await session.flush()
    return user


async def create_location(session: AsyncSession, faker) -> Location:
    location = Location(
        name=faker.company(),
        address=faker.address(),
        description=faker.text(max_nb_chars=50),
    )
    session.add(location)
    await session.flush()
    return location


async def create_room(
    session: AsyncSession,
    faker,
    *,
    location: Location,
    is_active: bool = True,
) -> Room:
    room = Room(
        location_id=location.id,
        name=faker.color_name(),
        capacity=faker.random_int(min=1, max=20),
        description=faker.text(max_nb_chars=40),
        is_active=is_active,
    )
    session.add(room)
    await session.flush()
    return room


async def create_timeslot(
    session: AsyncSession,
    *,
    room: Room,
    start_datetime: datetime,
    end_datetime: datetime,
    base_price: Decimal = Decimal("100.00"),
    status: TimeSlotStatus = TimeSlotStatus.AVAILABLE,
) -> TimeSlot:
    slot = TimeSlot(
        room_id=room.id,
        start_datetime=start_datetime,
        end_datetime=end_datetime,
        base_price=base_price,
        status=status,
    )
    session.add(slot)
    await session.flush()
    return slot


async def create_booking(
    session: AsyncSession,
    *,
    user: User,
    room: Room,
    timeslot: TimeSlot,
    status: BookingStatus = BookingStatus.PENDING_PAYMENTS,
    created_at: Optional[datetime] = None,
    expires_delta: timedelta = timedelta(minutes=30),
) -> Booking:
    booking = Booking(
        user_id=user.id,
        room_id=room.id,
        timeslot_id=timeslot.id,
        status=status,
        total_price=timeslot.base_price,
        paid_at=None,
        canceled_at=None,
        expires_at=timeslot.end_datetime + expires_delta,
    )
    if created_at is None:
        created_at = datetime.now(timezone.utc)
    booking.created_at = created_at
    session.add(booking)
    await session.flush()
    return booking
