from __future__ import annotations

from datetime import datetime


def _format_dt(dt: datetime) -> str:
    return dt.isoformat()


def login_ip(ip: str):
    return f"login:{ip}"


def locations_all() -> str:
    return "locations:all"


def timeslots_by_room_and_range(room_id: int, date_from: datetime, date_to: datetime) -> str:
    return f"timeslots:{room_id}:{_format_dt(date_from)}:{_format_dt(date_to)}"


def timeslots_room_prefix(room_id: int) -> str:
    return f"timeslots:{room_id}:*"


__all__ = [
    "timeslots_by_room_and_range",
    "timeslots_room_prefix",
]
