import pytest
from pydantic import ValidationError

from app.schemas.room import SRoomUpdate


def test_room_update_accepts_name_only():
    data = SRoomUpdate(name="Updated room")
    assert data.model_dump(exclude_unset=True) == {"name": "Updated room"}


def test_room_update_rejects_empty_payload():
    with pytest.raises(ValidationError) as exc_info:
        SRoomUpdate()
    errors = exc_info.value.errors()
    assert any("At least one field must be provided" in error["msg"] for error in errors)


def test_room_update_keeps_null_description():
    data = SRoomUpdate(description=None)
    assert data.model_dump(exclude_unset=True) == {"description": None}
