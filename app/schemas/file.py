from datetime import datetime
from enum import Enum
from typing import Literal

from app.models.file import FileStatus
from app.schemas import BaseSchema


class UploadType(str, Enum):
    PRESIGNED = "PRESIGNED"
    PROXY = "PROXY"

class SFileInitUploadIn(BaseSchema):
    original_name: str
    content_type: str
    size_bytes: int | None = None
    checksum_sha256: str | None = None
    mode: UploadType
    is_public: bool = False

class SFileUploadInstruction(BaseSchema):
    url: str
    method: Literal["PUT"]
    headers: dict[str, str] = {}
    expires_at: datetime | None = None

class SFileDownloadInstruction(BaseSchema):
    url: str
    method: Literal["GET"]
    expires_at: datetime | None = None

class SFileInitUploadOut(BaseSchema):
    file_id: int
    status: FileStatus
    bucket: str
    object_key: str
    upload: SFileUploadInstruction
    public_url: str | None = None

class SFileCompleteUploadIn(BaseSchema):
    etag: str | None = None
    size_bytes: int | None = None
    checksum_sha256: str | None = None

class SFileOut(BaseSchema):
    id: int
    created_at: datetime
    user_id: int
    original_name: str
    content_type: str
    size_bytes: int | None
    checksum_sha256: str | None
    status: FileStatus
    meta: dict
    is_public: bool
    public_url: str | None = None
