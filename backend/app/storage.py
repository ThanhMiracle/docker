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


STORAGE_BACKEND = os.getenv("STORAGE_BACKEND", "azure").lower()
MINIO_BUCKET = os.getenv("MINIO_BUCKET")
MINIO_PUBLIC_URL = os.getenv("MINIO_PUBLIC_URL")
MINIO_ENDPOINT_URL = os.getenv("MINIO_ENDPOINT_URL")
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY")
MINIO_AUTO_CREATE_BUCKET = os.getenv("MINIO_AUTO_CREATE_BUCKET", "").lower() in {
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


def _minio_client():
    return boto3.client(
        "s3",
        region_name="us-east-1",
        endpoint_url=MINIO_ENDPOINT_URL,
        aws_access_key_id=MINIO_ACCESS_KEY,
        aws_secret_access_key=MINIO_SECRET_KEY,
        config=Config(s3={"addressing_style": "path"}),
    )


def _ensure_local_bucket(client):
    if not MINIO_AUTO_CREATE_BUCKET:
        return
    try:
        client.head_bucket(Bucket=MINIO_BUCKET)
    except ClientError:
        client.create_bucket(Bucket=MINIO_BUCKET)
    client.put_bucket_policy(Bucket=MINIO_BUCKET, Policy=json.dumps({
        "Version": "2012-10-17",
        "Statement": [{
            "Effect": "Allow", "Principal": "*", "Action": "s3:GetObject",
            "Resource": f"arn:aws:s3:::{MINIO_BUCKET}/*",
        }],
    }))


def _put_minio_object(file_bytes: bytes, content_type: str, ext: str) -> str:
    if not MINIO_BUCKET:
        raise RuntimeError("MINIO_BUCKET is required")
    key = f"{uuid.uuid4().hex}{ext}"
    client = _minio_client()
    _ensure_local_bucket(client)
    client.put_object(Bucket=MINIO_BUCKET, Key=key, Body=file_bytes, ContentType=content_type)
    if not MINIO_PUBLIC_URL:
        raise RuntimeError("MINIO_PUBLIC_URL is required")
    return f"{MINIO_PUBLIC_URL.rstrip('/')}/{quote(key, safe='/')}"


def put_file(file_bytes: bytes, content_type: str, ext: str = "") -> str:
    if STORAGE_BACKEND == "azure":
        return _put_azure_blob(file_bytes, content_type, ext)
    if STORAGE_BACKEND == "minio":
        return _put_minio_object(file_bytes, content_type, ext)
    raise RuntimeError("STORAGE_BACKEND must be either 'minio' or 'azure'")
