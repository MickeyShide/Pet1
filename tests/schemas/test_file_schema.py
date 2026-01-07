import pytest
from pydantic import ValidationError

from app.models.file import FileStatus
from app.schemas.file import (
    SFileDownloadInstruction,
    SFileInitUploadIn,
    SFileInitUploadOut,
    SFileOut,
    SFileUploadInstruction,
)


def test__file_init_upload_in_rejects_extra_fields():
    with pytest.raises(ValidationError):
        SFileInitUploadIn(
            original_name="a.png",
            content_type="image/png",
            size_bytes=123,
            mode="PRESIGNED",
            extra="nope",
        )


def test__file_upload_instruction_requires_put_method():
    with pytest.raises(ValidationError):
        SFileUploadInstruction(url="http://test", method="POST")


def test__file_download_instruction_requires_get_method():
    with pytest.raises(ValidationError):
        SFileDownloadInstruction(url="http://test", method="PUT")


def test__file_init_upload_out_allows_public_url_none():
    payload = SFileInitUploadOut(
        file_id=1,
        status=FileStatus.PENDING,
        bucket="bucket",
        object_key="key",
        upload=SFileUploadInstruction(url="http://test", method="PUT"),
        public_url=None,
    )
    assert payload.public_url is None


def test__file_init_upload_out_allows_public_url_present():
    payload = SFileInitUploadOut(
        file_id=1,
        status=FileStatus.PENDING,
        bucket="bucket",
        object_key="key",
        upload=SFileUploadInstruction(url="http://test", method="PUT"),
        public_url="http://cdn.local/bucket/key",
    )
    assert payload.public_url == "http://cdn.local/bucket/key"


def test__file_out_rejects_extra_fields():
    with pytest.raises(ValidationError):
        SFileOut(
            id=1,
            created_at="2025-01-01T00:00:00Z",
            user_id=1,
            original_name="a.png",
            content_type="image/png",
            size_bytes=123,
            checksum_sha256=None,
            status=FileStatus.PENDING,
            meta={},
            is_public=True,
            public_url=None,
            extra="nope",
        )


def test__file_out_allows_public_url_null():
    payload = SFileOut(
        id=1,
        created_at="2025-01-01T00:00:00Z",
        user_id=1,
        original_name="a.png",
        content_type="image/png",
        size_bytes=123,
        checksum_sha256=None,
        status=FileStatus.PENDING,
        meta={},
        is_public=False,
        public_url=None,
    )
    assert payload.public_url is None
