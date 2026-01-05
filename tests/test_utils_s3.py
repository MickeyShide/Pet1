import boto3

from app.config import settings
from app.utils.s3 import get_s3


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

    client = get_s3()

    assert client == "client"
    assert captured["service_name"] == "s3"
    assert captured["endpoint_url"] == "http://example.com"
    assert captured["aws_access_key_id"] == "access"
    assert captured["aws_secret_access_key"] == "secret"
    assert captured["region_name"] == "us-test-1"
