import boto3

from app.config import settings


def get_s3():
    return boto3.client(
        "s3",
        endpoint_url=settings.S3_ENDPOINT_URL,
        aws_access_key_id=settings.S3_ACCESS_KEY,
        aws_secret_access_key=settings.S3_SECRET_KEY,
        region_name=settings.S3_REGION,
    )


def presign_put_object(bucket: str, key: str, content_type: str, expires: int) -> str:
    s3 = get_s3()
    return s3.generate_presigned_url(
        ClientMethod="put_object",
        Params={
            "Bucket": bucket,
            "Key": key,
            "ContentType": content_type,
        },
        ExpiresIn=expires,
    )


def presign_get_object(bucket: str, key: str, expires: int) -> str:
    s3 = get_s3()
    return s3.generate_presigned_url(
        ClientMethod="get_object",
        Params={
            "Bucket": bucket,
            "Key": key,
        },
        ExpiresIn=expires,
    )


def head_object(bucket: str, key: str) -> dict:
    s3 = get_s3()
    return s3.head_object(Bucket=bucket, Key=key)


def delete_object(bucket: str, key: str) -> None:
    s3 = get_s3()
    s3.delete_object(Bucket=bucket, Key=key)
