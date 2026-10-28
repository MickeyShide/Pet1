import pytest
from pydantic import ValidationError

from app.models.feature import FeatureType
from app.schemas.feature import SFeatureCreate, SFeatureUpdate


def test_feature_create_room_requires_room_id():
    with pytest.raises(ValidationError):
        SFeatureCreate(name="Projector", type=FeatureType.ROOM)


def test_feature_create_room_rejects_location_id():
    with pytest.raises(ValidationError):
        SFeatureCreate(name="Projector", type=FeatureType.ROOM, room_id=1, location_id=2)


def test_feature_create_location_requires_location_id():
    with pytest.raises(ValidationError):
        SFeatureCreate(name="Parking", type=FeatureType.LOCATION)


def test_feature_create_location_rejects_room_id():
    with pytest.raises(ValidationError):
        SFeatureCreate(name="Parking", type=FeatureType.LOCATION, location_id=1, room_id=2)


def test_feature_create_valid_room():
    data = SFeatureCreate(name="Projector", type=FeatureType.ROOM, room_id=1)
    assert data.room_id == 1


def test_feature_update_rejects_both_targets():
    with pytest.raises(ValidationError):
        SFeatureUpdate(room_id=1, location_id=2)


def test_feature_update_rejects_location_id_for_room_type():
    with pytest.raises(ValidationError):
        SFeatureUpdate(type=FeatureType.ROOM, location_id=1)


def test_feature_update_rejects_room_id_for_location_type():
    with pytest.raises(ValidationError):
        SFeatureUpdate(type=FeatureType.LOCATION, room_id=1)


def test_feature_update_allows_name_only():
    data = SFeatureUpdate(name="New")
    assert data.name == "New"
