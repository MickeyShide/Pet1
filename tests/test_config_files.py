from app.config import settings


def test__files_allowed_content_types_parsing():
    settings.FILES_ALLOWED_CONTENT_TYPES = "image/png, image/jpeg,application/pdf"
    assert settings.files_allowed_content_types == {"image/png", "image/jpeg", "application/pdf"}


def test__files_allowed_content_types_empty():
    settings.FILES_ALLOWED_CONTENT_TYPES = ""
    assert settings.files_allowed_content_types == set()


def test__s3_public_bucket_falls_back():
    settings.S3_PUBLIC_BUCKET = None
    settings.S3_BUCKET = "uploads"
    assert settings.s3_public_bucket == "uploads"


def test__s3_public_bucket_overrides():
    settings.S3_PUBLIC_BUCKET = "public-uploads"
    settings.S3_BUCKET = "uploads"
    assert settings.s3_public_bucket == "public-uploads"
