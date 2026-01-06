from __future__ import annotations

from datetime import datetime

from starlette import status
from starlette.exceptions import HTTPException


def sanitize_filename(original_name: str) -> str:
    if "\x00" in original_name:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="invalid_filename",
        )

    safe_name = original_name.replace("/", "_").replace("\\", "_")
    while ".." in safe_name:
        safe_name = safe_name.replace("..", "_")

    safe_name = safe_name.strip()
    if len(safe_name) > 120:
        safe_name = safe_name[:120]

    if not safe_name:
        return "file"

    return safe_name


def validate_content_type(content_type: str, allowed: set[str]) -> None:
    if content_type not in allowed:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="unsupported_media_type",
        )


def validate_size(
    mode: str,
    size_bytes: int | None,
    proxy_limit: int,
    presigned_limit: int,
) -> None:
    if size_bytes is None:
        return

    if size_bytes <= 0:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="invalid_file_size",
        )

    if mode == "PROXY" and size_bytes > proxy_limit:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="payload_too_large",
        )

    if mode == "PRESIGNED" and size_bytes > presigned_limit:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="payload_too_large",
        )


def build_object_key(
    env: str,
    user_id: int,
    dt: datetime,
    file_id: int,
    safe_name: str,
) -> str:
    year = f"{dt.year:04d}"
    month = f"{dt.month:02d}"
    return f"{env}/users/{user_id}/{year}/{month}/{file_id}/{safe_name}"


def build_public_url(base_url: str, bucket: str, key: str) -> str:
    base = base_url.rstrip("/")
    return f"{base}/{bucket}/{key}"
