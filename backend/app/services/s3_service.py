import uuid

import boto3

from app.core.config import settings

_client = boto3.client("s3", region_name=settings.aws_region)


def upload_file(user_id: uuid.UUID, document_id: uuid.UUID, filename: str, data: bytes, content_type: str) -> str:
    """Upload file to S3. Returns the S3 object key."""
    key = f"uploads/{user_id}/{document_id}/{filename}"
    _client.put_object(Bucket=settings.s3_bucket_name, Key=key, Body=data, ContentType=content_type)
    return key


def download_file(key: str) -> bytes:
    """Download file bytes from S3."""
    resp = _client.get_object(Bucket=settings.s3_bucket_name, Key=key)
    return resp["Body"].read()


def delete_file(key: str) -> None:
    """Delete a file from S3."""
    _client.delete_object(Bucket=settings.s3_bucket_name, Key=key)
