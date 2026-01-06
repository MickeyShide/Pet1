from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import Enum as SAEnum, Column, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, Relationship

from app.models import BaseSQLModel


class FileStatus(str, Enum):
    PENDING = "PENDING"
    UPLOADED = "UPLOADED"
    FAILED = "FAILED"
    DELETED = "DELETED"

if TYPE_CHECKING:
    from app.models.user import User

class File(BaseSQLModel, table=True):
    __tablename__ = "files"

    user_id: int = Field(foreign_key="users.id")
    user: "User" = Relationship(back_populates="files")

    bucket: str
    object_key: str
    original_name: str
    content_type: str
    size_bytes: int | None
    checksum_sha256: str | None
    status: FileStatus = Field(
        sa_type=SAEnum(FileStatus, name="pet1_filestatus")
    )
    is_public: bool = Field(default=False, nullable=False) # server_default = false is migration
    public_url: str | None = None
    meta: dict = Field(
        default_factory=dict,
        sa_column=Column(JSONB, nullable=False),
    )

    __table_args__ = (
        # Гарантия уникальности объекта в бакете
        UniqueConstraint(
            "bucket",
            "object_key",
            name="uq_files_bucket_object_key",
        ),
    )
