from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Booking, Feature, File, Image, Location, Room, TimeSlot, User
from app.models.booking import BookingStatus
from app.models.feature import FeatureType
from app.models.file import FileStatus
from app.models.image import ImageType
from app.models.room import RoomType, TimeSlotType
from app.models.timeslot import TimeSlotStatus
from app.models.user import UserRole


class UserFactory:
    @staticmethod
    async def create(
        session: AsyncSession,
        faker,
        *,
        role: UserRole = UserRole.USER,
        **overrides,
    ) -> User:
        user = User(
            first_name=overrides.get("first_name", faker.first_name()),
            second_name=overrides.get("second_name", faker.last_name()),
            email=overrides.get("email", faker.unique.email()),
            username=overrides.get("username", faker.unique.user_name()),
            hashed_password=overrides.get("hashed_password", faker.sha256(raw_output=False)),
            role=role,
        )
        session.add(user)
        await session.flush()
        return user


class LocationFactory:
    @staticmethod
    async def create(
        session: AsyncSession,
        faker,
        **overrides,
    ) -> Location:
        location = Location(
            name=overrides.get("name", faker.company()),
            address=overrides.get("address", faker.address()),
            description=overrides.get("description", faker.text(max_nb_chars=50)),
        )
        session.add(location)
        await session.flush()
        return location


class RoomFactory:
    @staticmethod
    async def create(
        session: AsyncSession,
        faker,
        *,
        location: Location,
        is_active: bool = True,
        hour_price: Decimal | None = None,
        time_slot_type: TimeSlotType = TimeSlotType.FLEXIBLE,
        room_type: RoomType | None = None,
        min_booking_duration_minutes: int | None = None,
        booking_step_minutes: int | None = None,
        **overrides,
    ) -> Room:
        if hour_price is None:
            hour_price = Decimal(faker.random_int(min=0, max=12312))
        room_kwargs = dict(
            location_id=location.id,
            name=overrides.get("name", faker.color_name()),
            capacity=overrides.get("capacity", faker.random_int(min=1, max=20)),
            description=overrides.get("description", faker.text(max_nb_chars=40)),
            is_active=is_active,
            hour_price=hour_price,
            time_slot_type=time_slot_type,
            type=room_type,
        )
        if min_booking_duration_minutes is not None:
            room_kwargs["min_booking_duration_minutes"] = min_booking_duration_minutes
        if booking_step_minutes is not None:
            room_kwargs["booking_step_minutes"] = booking_step_minutes
        if "location_id" in overrides:
            room_kwargs["location_id"] = overrides["location_id"]
        room = Room(**room_kwargs)
        session.add(room)
        await session.flush()
        return room


class TimeSlotFactory:
    @staticmethod
    async def create(
        session: AsyncSession,
        *,
        room: Room,
        start_datetime: datetime,
        end_datetime: datetime,
        base_price: Decimal = Decimal("100.00"),
        status: TimeSlotStatus = TimeSlotStatus.AVAILABLE,
        **overrides,
    ) -> TimeSlot:
        slot = TimeSlot(
            room_id=overrides.get("room_id", room.id),
            start_datetime=start_datetime,
            end_datetime=end_datetime,
            base_price=base_price,
            status=status,
        )
        session.add(slot)
        await session.flush()
        return slot


class BookingFactory:
    @staticmethod
    async def create(
        session: AsyncSession,
        *,
        user: User,
        room: Room,
        timeslot: TimeSlot,
        status: BookingStatus = BookingStatus.PENDING_PAYMENTS,
        created_at: Optional[datetime] = None,
        expires_delta: timedelta = timedelta(minutes=30),
        **overrides,
    ) -> Booking:
        booking = Booking(
            user_id=overrides.get("user_id", user.id),
            room_id=overrides.get("room_id", room.id),
            timeslot_id=overrides.get("timeslot_id", timeslot.id),
            status=status,
            total_price=overrides.get("total_price", timeslot.base_price),
            paid_at=overrides.get("paid_at"),
            canceled_at=overrides.get("canceled_at"),
            expires_at=datetime.now(timezone.utc) + expires_delta,
        )
        if created_at is None:
            created_at = datetime.now(timezone.utc)
        booking.created_at = created_at
        session.add(booking)
        await session.flush()
        return booking


class FeatureFactory:
    @staticmethod
    async def create(
        session: AsyncSession,
        faker,
        *,
        room: Room | None = None,
        location: Location | None = None,
        name: str | None = None,
        **overrides,
    ) -> Feature:
        if room is None and location is None:
            raise ValueError("room or location is required")
        if room is not None and location is not None:
            raise ValueError("feature cannot belong to both room and location")
        if name is None:
            name = faker.word()

        if room is not None:
            feature = Feature(
                name=name,
                type=FeatureType.ROOM,
                room_id=overrides.get("room_id", room.id),
            )
        else:
            feature = Feature(
                name=name,
                type=FeatureType.LOCATION,
                location_id=overrides.get("location_id", location.id),  # type: ignore[union-attr]
            )

        session.add(feature)
        await session.flush()
        return feature


class FileFactory:
    @staticmethod
    async def create(
        session: AsyncSession,
        *,
        user: User,
        bucket: str = "uploads",
        object_key: str = "files/sample.bin",
        original_name: str = "sample.bin",
        content_type: str = "application/octet-stream",
        size_bytes: int | None = 123,
        checksum_sha256: str | None = None,
        status: FileStatus = FileStatus.PENDING,
        is_public: bool = False,
        public_url: str | None = None,
        meta: dict | None = None,
        **overrides,
    ) -> File:
        file = File(
            user_id=overrides.get("user_id", user.id),
            bucket=overrides.get("bucket", bucket),
            object_key=overrides.get("object_key", object_key),
            original_name=overrides.get("original_name", original_name),
            content_type=overrides.get("content_type", content_type),
            size_bytes=overrides.get("size_bytes", size_bytes),
            checksum_sha256=overrides.get("checksum_sha256", checksum_sha256),
            status=overrides.get("status", status),
            is_public=overrides.get("is_public", is_public),
            public_url=overrides.get("public_url", public_url),
            meta=overrides.get("meta", meta or {}),
        )
        session.add(file)
        await session.flush()
        return file


class ImageFactory:
    @staticmethod
    async def create(
        session: AsyncSession,
        *,
        file: File,
        image1x: str | None = None,
        image2x: str | None = None,
        image_type: ImageType = ImageType.ROOM,
        room_id: int | None = None,
        location_id: int | None = None,
        **overrides,
    ) -> Image:
        image = Image(
            image1x=overrides.get("image1x", image1x),
            image2x=overrides.get("image2x", image2x),
            type=overrides.get("type", image_type),
            file_id=overrides.get("file_id", file.id),
            room_id=overrides.get("room_id", room_id),
            location_id=overrides.get("location_id", location_id),
        )
        session.add(image)
        await session.flush()
        return image


async def create_user(session: AsyncSession, faker, *, role: UserRole = UserRole.USER, **overrides) -> User:
    return await UserFactory.create(session, faker, role=role, **overrides)


async def create_location(session: AsyncSession, faker, **overrides) -> Location:
    return await LocationFactory.create(session, faker, **overrides)


async def create_room(
    session: AsyncSession,
    faker,
    *,
    location: Location,
    is_active: bool = True,
    hour_price: Decimal | None = None,
    time_slot_type: TimeSlotType = TimeSlotType.FLEXIBLE,
    room_type: RoomType | None = None,
    min_booking_duration_minutes: int | None = None,
    booking_step_minutes: int | None = None,
    **overrides,
) -> Room:
    return await RoomFactory.create(
        session,
        faker,
        location=location,
        is_active=is_active,
        hour_price=hour_price,
        time_slot_type=time_slot_type,
        room_type=room_type,
        min_booking_duration_minutes=min_booking_duration_minutes,
        booking_step_minutes=booking_step_minutes,
        **overrides,
    )


async def create_timeslot(
    session: AsyncSession,
    *,
    room: Room,
    start_datetime: datetime,
    end_datetime: datetime,
    base_price: Decimal = Decimal("100.00"),
    status: TimeSlotStatus = TimeSlotStatus.AVAILABLE,
    **overrides,
) -> TimeSlot:
    return await TimeSlotFactory.create(
        session,
        room=room,
        start_datetime=start_datetime,
        end_datetime=end_datetime,
        base_price=base_price,
        status=status,
        **overrides,
    )


async def create_booking(
    session: AsyncSession,
    *,
    user: User,
    room: Room,
    timeslot: TimeSlot,
    status: BookingStatus = BookingStatus.PENDING_PAYMENTS,
    created_at: Optional[datetime] = None,
    expires_delta: timedelta = timedelta(minutes=30),
    **overrides,
) -> Booking:
    return await BookingFactory.create(
        session,
        user=user,
        room=room,
        timeslot=timeslot,
        status=status,
        created_at=created_at,
        expires_delta=expires_delta,
        **overrides,
    )


async def create_feature(
    session: AsyncSession,
    faker,
    *,
    room: Room | None = None,
    location: Location | None = None,
    name: str | None = None,
    **overrides,
) -> Feature:
    return await FeatureFactory.create(
        session,
        faker,
        room=room,
        location=location,
        name=name,
        **overrides,
    )


async def create_file(
    session: AsyncSession,
    *,
    user: User,
    bucket: str = "uploads",
    object_key: str = "files/sample.bin",
    original_name: str = "sample.bin",
    content_type: str = "application/octet-stream",
    size_bytes: int | None = 123,
    checksum_sha256: str | None = None,
    status: FileStatus = FileStatus.PENDING,
    is_public: bool = False,
    public_url: str | None = None,
    meta: dict | None = None,
    **overrides,
) -> File:
    return await FileFactory.create(
        session,
        user=user,
        bucket=bucket,
        object_key=object_key,
        original_name=original_name,
        content_type=content_type,
        size_bytes=size_bytes,
        checksum_sha256=checksum_sha256,
        status=status,
        is_public=is_public,
        public_url=public_url,
        meta=meta,
        **overrides,
    )


async def create_image(
    session: AsyncSession,
    *,
    file: File,
    image1x: str | None = None,
    image2x: str | None = None,
    image_type: ImageType = ImageType.ROOM,
    room_id: int | None = None,
    location_id: int | None = None,
    **overrides,
) -> Image:
    return await ImageFactory.create(
        session,
        file=file,
        image1x=image1x,
        image2x=image2x,
        image_type=image_type,
        room_id=room_id,
        location_id=location_id,
        **overrides,
    )

