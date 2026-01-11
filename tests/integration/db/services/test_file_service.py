import pytest

from app.services.file import FileService
from app.utils import s3 as s3_utils


@pytest.mark.asyncio
async def test__file_service_presign_upload_calls_s3(monkeypatch):
    def fake_presign_put_object(bucket, key, content_type, expires):
        return f"url:{bucket}:{key}:{content_type}:{expires}"

    monkeypatch.setattr(s3_utils, "presign_put_object", fake_presign_put_object)

    result = await FileService(None).presign_upload_put("bucket", "key", "image/png", 123)
    assert result == "url:bucket:key:image/png:123"


@pytest.mark.asyncio
async def test__file_service_presign_download_calls_s3(monkeypatch):
    def fake_presign_get_object(bucket, key, expires):
        return f"url:{bucket}:{key}:{expires}"

    monkeypatch.setattr(s3_utils, "presign_get_object", fake_presign_get_object)

    result = await FileService(None).presign_download_get("bucket", "key", 321)
    assert result == "url:bucket:key:321"


@pytest.mark.asyncio
async def test__file_service_head_calls_s3(monkeypatch):
    def fake_head_object(bucket, key):
        return {"ContentLength": 1}

    monkeypatch.setattr(s3_utils, "head_object", fake_head_object)

    result = await FileService(None).head("bucket", "key")
    assert result == {"ContentLength": 1}


@pytest.mark.asyncio
async def test__file_service_delete_calls_s3(monkeypatch):
    calls = []

    def fake_delete_object(bucket, key):
        calls.append((bucket, key))

    monkeypatch.setattr(s3_utils, "delete_object", fake_delete_object)

    await FileService(None).delete_object("bucket", "key")
    assert calls == [("bucket", "key")]
