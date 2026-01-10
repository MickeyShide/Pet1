from __future__ import annotations

from typing import Any, Mapping

from pydantic import BaseModel


def response_with_example(
    description: str,
    example: Any,
    model: type[BaseModel] | None = None,
) -> dict:
    response = {
        "description": description,
        "content": {
            "application/json": {
                "example": example,
            }
        },
    }
    if model is not None:
        response["model"] = model
    return response


def error_response(description: str, examples: Mapping[str, dict]) -> dict:
    return {
        "description": description,
        "content": {
            "application/json": {
                "examples": examples,
            }
        },
    }


def example(summary: str, value: dict) -> dict:
    return {"summary": summary, "value": value}


def validation_error_example(
    message: str,
    loc: list[Any],
    input_value: Any,
    error_type: str = "value_error",
) -> dict:
    return {
        "detail": [
            {
                "loc": loc,
                "msg": message,
                "type": error_type,
                "input": input_value,
            }
        ]
    }


VALIDATION_ERROR_EXAMPLE = validation_error_example(
    "field required",
    ["body", "field"],
    None,
    "missing",
)

USER_EXAMPLE = {
    "id": 42,
    "first_name": "Alex",
    "second_name": "Smith",
    "email": "alex@example.com",
    "username": "alex",
    "role": "USER",
}

LOGIN_OUT_EXAMPLE = {
    "access_token": "access-token",
    "user": USER_EXAMPLE,
}

FEATURE_ROOM_EXAMPLE = {
    "id": 1,
    "name": "Wi-Fi",
    "type": "ROOM",
    "room_id": 10,
    "location_id": None,
}

FEATURE_LOCATION_EXAMPLE = {
    "id": 2,
    "name": "Parking",
    "type": "LOCATION",
    "room_id": None,
    "location_id": 5,
}

LOCATION_EXAMPLE = {
    "id": 5,
    "name": "Downtown Hub",
    "address": "1 Main St",
    "description": "Cozy workspace in city center",
    "features": [FEATURE_LOCATION_EXAMPLE],
}

ROOM_EXAMPLE = {
    "id": 10,
    "location_id": 5,
    "name": "Studio 2",
    "capacity": 6,
    "description": "Bright room with natural light",
    "type": "STUDIO",
    "time_slot_type": "FLEXIBLE",
    "min_booking_duration_minutes": 60,
    "booking_step_minutes": 30,
    "hour_price": 25.5,
    "is_active": True,
    "features": [FEATURE_ROOM_EXAMPLE],
}

ROOM_WITH_LOCATION_EXAMPLE = {
    **ROOM_EXAMPLE,
    "location": LOCATION_EXAMPLE,
}

TIMESLOT_EXAMPLE = {
    "id": 100,
    "room_id": 10,
    "start_datetime": "2024-05-01T10:00:00+00:00",
    "end_datetime": "2024-05-01T11:00:00+00:00",
    "base_price": 25.5,
    "status": "AVAILABLE",
}

TIMESLOT_WITH_BOOKING_STATUS_EXAMPLE = {
    **TIMESLOT_EXAMPLE,
    "has_active_booking": False,
}

TIMESLOT_RANGE_EXAMPLE = {
    "id": "100",
    "date_from": "2024-05-01T10:00:00+00:00",
    "date_to": "2024-05-01T11:00:00+00:00",
    "label": "10:00 - 11:00",
    "hours": 1.0,
}

PRICE_QUOTE_EXAMPLE = {
    "price": 51.0,
}

BOOKING_OUT_AFTER_CREATE_EXAMPLE = {
    "id": 500,
    "status": "PENDING_PAYMENTS",
    "timeslot_id": 100,
    "total_price": 25.5,
    "expires_at": "2024-05-01T09:55:00+00:00",
}

BOOKING_OUT_EXAMPLE = {
    "id": 500,
    "user_id": 42,
    "room_id": 10,
    "timeslot_id": 100,
    "status": "PENDING_PAYMENTS",
    "total_price": 25.5,
    "paid_at": None,
    "canceled_at": None,
    "expires_at": "2024-05-01T09:55:00+00:00",
    "room": ROOM_EXAMPLE,
}

BOOKING_WITH_TIMESLOT_EXAMPLE = {
    "booking": BOOKING_OUT_EXAMPLE,
    "timeslot": TIMESLOT_EXAMPLE,
}

PAYMENT_EXAMPLE = {
    "id": 900,
    "booking_id": 500,
    "external_id": "pay_123",
    "status": "CREATED",
}

IMAGE_PRESIGN_EXAMPLE = {
    "id": 77,
    "upload_url": "https://s3.example.com/uploads/77",
    "public_url": "https://cdn.example.com/images/77.jpg",
}
