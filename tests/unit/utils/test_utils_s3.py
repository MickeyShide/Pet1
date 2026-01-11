import boto3

from app.config import settings
from app.utils import s3 as s3_utils


def test__get_s3_uses_settings(monkeypatch):
    captured = {}

    def fake_client(service_name, **kwargs):
        captured["service_name"] = service_name
        captured.update(kwargs)
        return "client"

    monkeypatch.setattr(boto3, "client", fake_client)
    monkeypatch.setattr(settings, "S3_ENDPOINT_URL", "http://example.com")
    monkeypatch.setattr(settings, "S3_ACCESS_KEY", "access")
    monkeypatch.setattr(settings, "S3_SECRET_KEY", "secret")
    monkeypatch.setattr(settings, "S3_REGION", "us-test-1")

    client = s3_utils.get_s3()

    assert client == "client"
    assert captured["service_name"] == "s3"
    assert captured["endpoint_url"] == "http://example.com"
    assert captured["aws_access_key_id"] == "access"
    assert captured["aws_secret_access_key"] == "secret"
    assert captured["region_name"] == "us-test-1"


def test__presign_put_object_uses_params(monkeypatch):
    calls = []

    class StubClient:
        def generate_presigned_url(self, ClientMethod, Params, ExpiresIn):
            calls.append((ClientMethod, Params, ExpiresIn))
            return "url"

    monkeypatch.setattr(boto3, "client", lambda *args, **kwargs: StubClient())

    url = s3_utils.presign_put_object("bucket", "key", "image/png", 123)
    assert url == "url"
    assert calls == [
        (
            "put_object",
            {"Bucket": "bucket", "Key": "key", "ContentType": "image/png"},
            123,
        )
    ]


def test__presign_get_object_uses_params(monkeypatch):
    calls = []

    class StubClient:
        def generate_presigned_url(self, ClientMethod, Params, ExpiresIn):
            calls.append((ClientMethod, Params, ExpiresIn))
            return "url"

    monkeypatch.setattr(boto3, "client", lambda *args, **kwargs: StubClient())

    url = s3_utils.presign_get_object("bucket", "key", 321)
    assert url == "url"
    assert calls == [("get_object", {"Bucket": "bucket", "Key": "key"}, 321)]


def test__head_object_uses_params(monkeypatch):
    calls = []

    class StubClient:
        def head_object(self, Bucket, Key):
            calls.append((Bucket, Key))
            return {"ContentLength": 1}

    monkeypatch.setattr(boto3, "client", lambda *args, **kwargs: StubClient())

    result = s3_utils.head_object("bucket", "key")
    assert result == {"ContentLength": 1}
    assert calls == [("bucket", "key")]


def test__delete_object_uses_params(monkeypatch):
    calls = []

    class StubClient:
        def delete_object(self, Bucket, Key):
            calls.append((Bucket, Key))

    monkeypatch.setattr(boto3, "client", lambda *args, **kwargs: StubClient())

    s3_utils.delete_object("bucket", "key")
    assert calls == [("bucket", "key")]
