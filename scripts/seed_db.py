#!/usr/bin/env python3
import argparse
import asyncio
import random
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import uuid4

from faker import Faker

from app.config import settings
from app.db import base as db_base
from app.models import Booking, Feature, File, Image, Location, Payment, Room, TimeSlot, User
from app.models.booking import BookingStatus
from app.models.feature import FeatureType
from app.models.file import FileStatus
from app.models.image import ImageType
from app.models.payment import PaymentStatus
from app.models.room import RoomType, TimeSlotType
from app.models.timeslot import TimeSlotStatus
from app.models.user import UserRole

LOCATION_FEATURES = [
    "Free parking",
    "Cafe",
    "Reception",
    "Security",
    "Wheelchair access",
    "Restrooms",
    "Public transport",
    "24/7 access",
    "Lockers",
    "Outdoor terrace",
    "Pet friendly",
    "Bike storage",
]

ROOM_FEATURES = [
    "Projector",
    "Whiteboard",
    "HDMI",
    "Sound system",
    "Natural light",
    "Air conditioning",
    "Blackout curtains",
    "Recording gear",
    "Microphones",
    "TV",
    "WiFi",
    "Ergonomic chairs",
]

MIN_STEP_OPTIONS = [
    (30, 30),
    (60, 30),
    (60, 60),
    (90, 30),
    (90, 45),
    (120, 60),
]


@dataclass
class Counters:
    file_index: int = 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Seed the database with realistic bulk test data.",
    )
    parser.add_argument("--locations", type=int, default=1000)
    parser.add_argument("--rooms-per-location", type=int, default=4)
    parser.add_argument("--timeslots-per-room", type=int, default=24)
    parser.add_argument("--features-per-location", type=int, default=6)
    parser.add_argument("--features-per-room", type=int, default=8)
    parser.add_argument("--images-per-location", type=int, default=3)
    parser.add_argument("--images-per-room", type=int, default=4)
    parser.add_argument("--users", type=int, default=400)
    parser.add_argument("--bookings-per-room", type=int, default=3)
    parser.add_argument("--commit-every", type=int, default=20)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--quiet", action="store_true")
    parser.add_argument("--sql-echo", action="store_true")
    return parser.parse_args()


def generate_feature_names(pool: list[str], count: int, rng: random.Random) -> list[str]:
    if count <= 0:
        return []
    if count <= len(pool):
        return rng.sample(pool, count)
    names = []
    for i in range(count):
        base = pool[i % len(pool)]
        suffix = "" if i < len(pool) else f" {i // len(pool) + 1}"
        names.append(base + suffix)
    rng.shuffle(names)
    return names


def make_object_key(prefix: str, extension: str, counters: Counters) -> str:
    counters.file_index += 1
    return f"{prefix}/{counters.file_index:09d}-{uuid4().hex}.{extension}"


def build_user(faker: Faker, i: int) -> User:
    first = faker.first_name()
    last = faker.last_name()
    username = f"{first.lower()}.{last.lower()}{i}"
    email = f"{username}@example.com"
    role = UserRole.ADMIN if i == 0 else UserRole.USER
    return User(
        first_name=first,
        second_name=last,
        email=email,
        username=username,
        hashed_password=faker.sha256(raw_output=False),
        role=role,
    )


def build_location(faker: Faker) -> Location:
    return Location(
        name=faker.company(),
        address=faker.address().replace("\n", ", "),
        description=faker.text(max_nb_chars=120),
    )


def build_room(faker: Faker, rng: random.Random, location_id: int) -> Room:
    min_duration, step = rng.choice(MIN_STEP_OPTIONS)
    room_type = rng.choice(list(RoomType)) if rng.random() < 0.9 else None
    time_slot_type = rng.choice(list(TimeSlotType))
    hour_price = Decimal(rng.randrange(20, 200, 5)).quantize(Decimal("0.01"))
    return Room(
        location_id=location_id,
        name=f"{faker.color_name()} {faker.word().title()}",
        capacity=rng.randint(2, 40),
        description=faker.text(max_nb_chars=80),
        type=room_type,
        time_slot_type=time_slot_type,
        min_booking_duration_minutes=min_duration,
        booking_step_minutes=step,
        hour_price=hour_price,
        is_active=rng.random() < 0.92,
    )


def build_timeslots(
    room: Room,
    count: int,
    rng: random.Random,
    base_date: datetime,
) -> list[TimeSlot]:
    slots = []
    if count <= 0:
        return slots
    slot_minutes = max(room.booking_step_minutes, 30)
    day_start_hour = 8
    day_end_hour = 20
    current = base_date.replace(hour=day_start_hour, minute=0, second=0, microsecond=0)
    while len(slots) < count:
        end = current + timedelta(minutes=slot_minutes)
        if end.hour > day_end_hour or (end.hour == day_end_hour and end.minute > 0):
            current = (current + timedelta(days=1)).replace(
                hour=day_start_hour, minute=0, second=0, microsecond=0
            )
            continue
        status = rng.choices(
            [TimeSlotStatus.AVAILABLE, TimeSlotStatus.BLOCKED, TimeSlotStatus.CANCELED],
            weights=[80, 15, 5],
            k=1,
        )[0]
        base_price = (room.hour_price * Decimal(slot_minutes) / Decimal(60)).quantize(Decimal("0.01"))
        slots.append(
            TimeSlot(
                room_id=room.id,
                start_datetime=current,
                end_datetime=end,
                base_price=base_price,
                status=status,
            )
        )
        current = end
    return slots


def build_booking(
    rng: random.Random,
    now: datetime,
    user_id: int,
    room_id: int,
    timeslot: TimeSlot,
) -> Booking:
    status = rng.choices(
        [
            BookingStatus.PAID,
            BookingStatus.PENDING_PAYMENTS,
            BookingStatus.CANCELED,
            BookingStatus.EXPIRED,
        ],
        weights=[55, 25, 10, 10],
        k=1,
    )[0]

    if status == BookingStatus.PENDING_PAYMENTS:
        created_at = now - timedelta(minutes=rng.randint(1, 10))
        expires_at = now + timedelta(minutes=rng.randint(10, 60))
        paid_at = None
        canceled_at = None
    else:
        created_at = now - timedelta(days=rng.randint(1, 30))
        expires_at = created_at + timedelta(minutes=30)
        paid_at = created_at + timedelta(minutes=rng.randint(1, 20)) if status == BookingStatus.PAID else None
        canceled_at = (
            created_at + timedelta(minutes=rng.randint(1, 20))
            if status == BookingStatus.CANCELED
            else None
        )

    booking = Booking(
        user_id=user_id,
        room_id=room_id,
        timeslot_id=timeslot.id,
        status=status,
        total_price=timeslot.base_price,
        paid_at=paid_at,
        canceled_at=canceled_at,
        expires_at=expires_at,
    )
    booking.created_at = created_at
    return booking


def build_payment_for_booking(rng: random.Random, booking: Booking) -> Payment | None:
    if booking.status == BookingStatus.PAID:
        status = PaymentStatus.SUCCESS
    elif booking.status == BookingStatus.PENDING_PAYMENTS:
        status = PaymentStatus.CREATED
    else:
        if rng.random() > 0.35:
            return None
        status = PaymentStatus.FAILED
    return Payment(
        booking_id=booking.id,
        external_id=f"PAY-{uuid4().hex[:12]}",
        status=status,
    )


async def seed_db(args: argparse.Namespace) -> None:
    db_base.init_engine(echo=args.sql_echo)
    faker = Faker("en_US")
    faker.seed_instance(args.seed)
    rng = random.Random(args.seed)
    counters = Counters()
    now = datetime.now(timezone.utc)
    commit_every = max(1, args.commit_every)

    async with db_base.async_session_maker() as session:
        user_objects: list[User] = []
        for i in range(args.users):
            user = build_user(faker, i)
            session.add(user)
            user_objects.append(user)
            if (i + 1) % 200 == 0:
                await session.flush()
        await session.commit()
        users = [user.id for user in user_objects if user.id is not None]

        if not users:
            raise RuntimeError("No users created, aborting.")

        created_locations = 0
        total_rooms = 0
        total_timeslots = 0
        total_features = 0
        total_images = 0
        total_files = 0
        total_bookings = 0
        total_payments = 0

        public_base = settings.S3_PUBLIC_BASE_URL.rstrip("/")
        public_bucket = settings.s3_public_bucket
        for loc_index in range(args.locations):
            location = build_location(faker)
            session.add(location)
            await session.flush()

            location_feature_names = generate_feature_names(
                LOCATION_FEATURES,
                args.features_per_location,
                rng,
            )
            location_features = [
                Feature(
                    name=name,
                    type=FeatureType.LOCATION,
                    location_id=location.id,
                )
                for name in location_feature_names
            ]
            session.add_all(location_features)
            total_features += len(location_features)

            rooms = [build_room(faker, rng, location.id) for _ in range(args.rooms_per_location)]
            session.add_all(rooms)
            await session.flush()
            total_rooms += len(rooms)

            file_objects: list[File] = []
            image_jobs: list[tuple[File, ImageType, int | None, int | None]] = []
            for _ in range(args.images_per_location):
                file_obj = File(
                    user_id=rng.choice(users),
                    bucket=settings.S3_BUCKET,
                    object_key=make_object_key("images/locations", "jpg", counters),
                    original_name=f"location-{location.id}.jpg",
                    content_type="image/jpeg",
                    size_bytes=rng.randint(50_000, 2_000_000),
                    checksum_sha256=faker.sha256(raw_output=False),
                    status=FileStatus.UPLOADED,
                    is_public=True,
                    public_url=None,
                    meta={"width": 1600, "height": 900},
                )
                file_obj.public_url = f"{public_base}/{public_bucket}/{file_obj.object_key}"
                file_objects.append(file_obj)
                image_jobs.append((file_obj, ImageType.LOCATION, None, location.id))

            for room in rooms:
                room_feature_names = generate_feature_names(
                    ROOM_FEATURES,
                    args.features_per_room,
                    rng,
                )
                room_features = [
                    Feature(
                        name=name,
                        type=FeatureType.ROOM,
                        room_id=room.id,
                    )
                    for name in room_feature_names
                ]
                session.add_all(room_features)
                total_features += len(room_features)

                for _ in range(args.images_per_room):
                    file_obj = File(
                        user_id=rng.choice(users),
                        bucket=settings.S3_BUCKET,
                        object_key=make_object_key("images/rooms", "jpg", counters),
                        original_name=f"room-{room.id}.jpg",
                        content_type="image/jpeg",
                        size_bytes=rng.randint(40_000, 1_500_000),
                        checksum_sha256=faker.sha256(raw_output=False),
                        status=FileStatus.UPLOADED,
                        is_public=True,
                        public_url=None,
                        meta={"width": 1400, "height": 900},
                    )
                    file_obj.public_url = f"{public_base}/{public_bucket}/{file_obj.object_key}"
                    file_objects.append(file_obj)
                    image_jobs.append((file_obj, ImageType.ROOM, room.id, None))

            session.add_all(file_objects)
            await session.flush()

            images = []
            for file_obj, image_type, room_id, location_id in image_jobs:
                images.append(
                    Image(
                        image1x=file_obj.public_url,
                        image2x=file_obj.public_url,
                        type=image_type,
                        file_id=file_obj.id,
                        room_id=room_id,
                        location_id=location_id,
                    )
                )
            session.add_all(images)
            total_files += len(file_objects)
            total_images += len(images)

            all_timeslots: dict[int, list[TimeSlot]] = {}
            for room in rooms:
                base_date = now + timedelta(days=rng.randint(0, 14))
                slots = build_timeslots(room, args.timeslots_per_room, rng, base_date)
                all_timeslots[room.id] = slots
                session.add_all(slots)
                total_timeslots += len(slots)
            await session.flush()

            for room in rooms:
                slots = all_timeslots.get(room.id, [])
                if not slots or args.bookings_per_room <= 0:
                    continue
                booking_count = min(args.bookings_per_room, len(slots))
                chosen = rng.sample(slots, booking_count)
                bookings = [
                    build_booking(rng, now, rng.choice(users), room.id, slot) for slot in chosen
                ]
                session.add_all(bookings)
                await session.flush()
                total_bookings += len(bookings)
                for booking in bookings:
                    payment = build_payment_for_booking(rng, booking)
                    if payment is not None:
                        session.add(payment)
                        total_payments += 1

            created_locations += 1
            if created_locations % commit_every == 0:
                await session.commit()
                session.expunge_all()
                if not args.quiet:
                    print(f"Committed {created_locations}/{args.locations} locations...")

        await session.commit()

    await db_base.dispose_engine()
    if not args.quiet:
        print("Seed complete:")
        print(f"  locations:  {created_locations}")
        print(f"  rooms:      {total_rooms}")
        print(f"  timeslots:  {total_timeslots}")
        print(f"  features:   {total_features}")
        print(f"  files:      {total_files}")
        print(f"  images:     {total_images}")
        print(f"  bookings:   {total_bookings}")
        print(f"  payments:   {total_payments}")


def main() -> None:
    args = parse_args()
    asyncio.run(seed_db(args))


if __name__ == "__main__":
    main()
