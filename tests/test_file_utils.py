from datetime import datetime

import pytest
from starlette.exceptions import HTTPException

from app.utils.file_utils import (
    sanitize_filename,
    validate_content_type,
    validate_size,
    build_object_key,
    build_public_url,
)


def test__sanitize_filename_replaces_paths_and_trims():
    assert sanitize_filename("  foo/bar\\baz  ") == "foo_bar_baz"


def test__sanitize_filename_replaces_dotdot():
    assert sanitize_filename("a..b") == "a_b"


def test__sanitize_filename_rejects_null_byte():
    with pytest.raises(HTTPException) as exc:
        sanitize_filename("bad\x00name.png")
    assert exc.value.status_code == 422


def test__sanitize_filename_empty_defaults():
    assert sanitize_filename("   ") == "file"


def test__sanitize_filename_truncates_long_names():
    name = "a" * 200
    assert len(sanitize_filename(name)) == 120


def test__validate_content_type_allows_whitelist():
    validate_content_type("image/png", {"image/png"})


def test__validate_content_type_rejects_unknown():
    with pytest.raises(HTTPException) as exc:
        validate_content_type("image/jpeg", {"image/png"})
    assert exc.value.status_code == 415


def test__validate_size_allows_none():
    validate_size("PRESIGNED", None, 10, 20)


def test__validate_size_rejects_non_positive():
    with pytest.raises(HTTPException) as exc:
        validate_size("PRESIGNED", 0, 10, 20)
    assert exc.value.status_code == 422


def test__validate_size_rejects_proxy_limit():
    with pytest.raises(HTTPException) as exc:
        validate_size("PROXY", 11, 10, 20)
    assert exc.value.status_code == 413


def test__validate_size_rejects_presigned_limit():
    with pytest.raises(HTTPException) as exc:
        validate_size("PRESIGNED", 21, 10, 20)
    assert exc.value.status_code == 413


def test__build_object_key_format():
    dt = datetime(2025, 1, 2)
    key = build_object_key("dev", 7, dt, 123, "name.png")
    assert key == "dev/users/7/2025/01/123/name.png"


def test__build_public_url_normalizes_base():
    assert build_public_url("http://cdn.local/", "bucket", "path/file.png") == (
        "http://cdn.local/bucket/path/file.png"
    )
