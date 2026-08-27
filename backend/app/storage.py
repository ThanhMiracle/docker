"""Upload adapter supporting local MinIO/S3 and Azure Blob Storage."""

import os
import uuid
import json
from urllib.parse import quote

import boto3
from azure.core.exceptions import ResourceExistsError
from azure.storage.blob import BlobServiceClient, ContentSettings
from botocore.config import Config
from botocore.exceptions import ClientError


STORAGE_BACKEND = os.getenv("STORAGE_BACKEND", "s3").lower()
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
AWS_S3_BUCKET = os.getenv("AWS_S3_BUCKET")
AWS_S3_PUBLIC_URL = os.getenv("AWS_S3_PUBLIC_URL")
AWS_S3_ENDPOINT_URL = os.getenv("AWS_S3_ENDPOINT_URL")
AWS_S3_AUTO_CREATE_BUCKET = os.getenv("AWS_S3_AUTO_CREATE_BUCKET", "").lower() in {
    "1", "true", "yes"
}
AZURE_STORAGE_CONNECTION_STRING = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
AZURE_STORAGE_CONTAINER = os.getenv("AZURE_STORAGE_CONTAINER")
# Optional CDN or public-container URL, for example https://cdn.example.com/products.
AZURE_BLOB_PUBLIC_URL = os.getenv("AZURE_BLOB_PUBLIC_URL", "")


def _azure_container_client():
    if not AZURE_STORAGE_CONNECTION_STRING:
        raise RuntimeError("AZURE_STORAGE_CONNECTION_STRING is required")
    if not AZURE_STORAGE_CONTAINER:
        raise RuntimeError("AZURE_STORAGE_CONTAINER is required")

    service = BlobServiceClient.from_connection_string(
        AZURE_STORAGE_CONNECTION_STRING
    )
    container = service.get_container_client(AZURE_STORAGE_CONTAINER)
    try:
        container.create_container()
    except ResourceExistsError:
        pass
    return container


def _put_azure_blob(file_bytes: bytes, content_type: str, ext: str) -> str:
    key = f"products/{uuid.uuid4().hex}{ext}"
    container = _azure_container_client()
    blob = container.get_blob_client(key)
    blob.upload_blob(
        file_bytes,
        blob_type="BlockBlob",
        overwrite=False,
        content_settings=ContentSettings(content_type=content_type),
    )

    if AZURE_BLOB_PUBLIC_URL:
        return f"{AZURE_BLOB_PUBLIC_URL.rstrip('/')}/{quote(key, safe='/')}"
    return blob.url


def _s3_client():
    return boto3.client(
        "s3",
        region_name=AWS_REGION,
        endpoint_url=AWS_S3_ENDPOINT_URL,
        config=Config(s3={"addressing_style": "path"}) if AWS_S3_ENDPOINT_URL else None,
    )


def _ensure_local_bucket(client):
    if not AWS_S3_AUTO_CREATE_BUCKET:
        return
    try:
        client.head_bucket(Bucket=AWS_S3_BUCKET)
    except ClientError:
        client.create_bucket(Bucket=AWS_S3_BUCKET)
    client.put_bucket_policy(Bucket=AWS_S3_BUCKET, Policy=json.dumps({
        "Version": "2012-10-17",
        "Statement": [{
            "Effect": "Allow", "Principal": "*", "Action": "s3:GetObject",
            "Resource": f"arn:aws:s3:::{AWS_S3_BUCKET}/*",
        }],
    }))


def _put_s3_object(file_bytes: bytes, content_type: str, ext: str) -> str:
    if not AWS_S3_BUCKET:
        raise RuntimeError("AWS_S3_BUCKET is required")
    key = f"{uuid.uuid4().hex}{ext}"
    client = _s3_client()
    _ensure_local_bucket(client)
    client.put_object(Bucket=AWS_S3_BUCKET, Key=key, Body=file_bytes, ContentType=content_type)
    if AWS_S3_PUBLIC_URL:
        return f"{AWS_S3_PUBLIC_URL.rstrip('/')}/{quote(key, safe='/')}"
    if AWS_REGION == "us-east-1":
        return f"https://{AWS_S3_BUCKET}.s3.amazonaws.com/{key}"
    return f"https://{AWS_S3_BUCKET}.s3.{AWS_REGION}.amazonaws.com/{key}"


def put_file(file_bytes: bytes, content_type: str, ext: str = "") -> str:
    if STORAGE_BACKEND == "azure":
        return _put_azure_blob(file_bytes, content_type, ext)
    if STORAGE_BACKEND == "s3":
        return _put_s3_object(file_bytes, content_type, ext)
    raise RuntimeError("STORAGE_BACKEND must be either 's3' or 'azure'")
