"""Upload adapter supporting local MinIO/S3 and Azure Blob Storage."""

import os
import uuid
import json
import re
from functools import lru_cache
from urllib.parse import quote

import boto3
from azure.core.exceptions import ResourceExistsError
from azure.identity import DefaultAzureCredential
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
AZURE_STORAGE_ACCOUNT_URL = os.getenv("AZURE_STORAGE_ACCOUNT_URL", "").strip()
AZURE_STORAGE_CONTAINER = os.getenv("AZURE_STORAGE_CONTAINER", "products")
AZURE_CLIENT_ID = os.getenv("AZURE_CLIENT_ID", "").strip()
AZURE_STORAGE_AUTO_CREATE_CONTAINER = os.getenv(
    "AZURE_STORAGE_AUTO_CREATE_CONTAINER", "false"
).lower() in {"1", "true", "yes"}
# Optional CDN or public-container URL, for example https://cdn.example.com/products.
AZURE_BLOB_PUBLIC_URL = os.getenv("AZURE_BLOB_PUBLIC_URL", "")
# Stable browser URL through the API for blobs in a private container.
AZURE_BLOB_PROXY_URL = os.getenv("AZURE_BLOB_PROXY_URL", "/api/files/images")


class StorageConfigurationError(RuntimeError):
    """Storage settings are missing; retrying the upload cannot resolve this."""


@lru_cache(maxsize=1)
def _azure_service_client():
    if AZURE_STORAGE_ACCOUNT_URL:
        # Reuse the credential/client so access tokens and HTTP connections are cached.
        credential = DefaultAzureCredential(
            managed_identity_client_id=AZURE_CLIENT_ID or None,
        )
        return BlobServiceClient(
            account_url=AZURE_STORAGE_ACCOUNT_URL, credential=credential,
        )
    if AZURE_STORAGE_CONNECTION_STRING:
        return BlobServiceClient.from_connection_string(
            AZURE_STORAGE_CONNECTION_STRING,
        )
    raise StorageConfigurationError(
        "AZURE_STORAGE_ACCOUNT_URL is required for managed identity "
        "(or set AZURE_STORAGE_CONNECTION_STRING for connection-string authentication)"
    )


def _azure_container_client():
    if not AZURE_STORAGE_CONTAINER:
        raise StorageConfigurationError("AZURE_STORAGE_CONTAINER is required")
    return _azure_service_client().get_container_client(AZURE_STORAGE_CONTAINER)


def _put_azure_blob(file_bytes: bytes, content_type: str, ext: str, key=None) -> str:
    key = key or f"products/{uuid.uuid4().hex}{ext}"
    container = _azure_container_client()
    if AZURE_STORAGE_AUTO_CREATE_CONTAINER:
        try:
            container.create_container()
        except ResourceExistsError:
            pass
    blob = container.get_blob_client(key)
    blob.upload_blob(
        file_bytes,
        blob_type="BlockBlob",
        overwrite=False,
        content_settings=ContentSettings(content_type=content_type),
    )

    if AZURE_BLOB_PUBLIC_URL:
        return f"{AZURE_BLOB_PUBLIC_URL.rstrip('/')}/{quote(key, safe='/')}"
    return f"{AZURE_BLOB_PROXY_URL.rstrip('/')}/{quote(key, safe='/')}"


def get_image(key: str):
    """Read an uploaded Blob through the API, without making its container public."""
    if STORAGE_BACKEND != "azure":
        raise ValueError("Blob image reads require the Azure storage backend")
    # Only expose the upload namespace, never other objects in the container.
    if not key.startswith("products/") or any(
        part in {"", ".", ".."} for part in key.split("/")
    ):
        raise ValueError("Invalid image key")
    download = _azure_container_client().get_blob_client(key).download_blob()
    content_type = download.properties.content_settings.content_type
    return download.chunks(), content_type or "application/octet-stream", download.size


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


def _put_minio_object(file_bytes: bytes, content_type: str, ext: str, key=None) -> str:
    if not MINIO_BUCKET:
        raise StorageConfigurationError("MINIO_BUCKET is required")
    if not MINIO_PUBLIC_URL:
        raise StorageConfigurationError("MINIO_PUBLIC_URL is required")
    key = key or f"{uuid.uuid4().hex}{ext}"
    client = _minio_client()
    _ensure_local_bucket(client)
    client.put_object(Bucket=MINIO_BUCKET, Key=key, Body=file_bytes, ContentType=content_type)
    return f"{MINIO_PUBLIC_URL.rstrip('/')}/{quote(key, safe='/')}"


def put_file(file_bytes: bytes, content_type: str, ext: str = "") -> str:
    if STORAGE_BACKEND == "azure":
        return _put_azure_blob(file_bytes, content_type, ext)
    if STORAGE_BACKEND == "minio":
        return _put_minio_object(file_bytes, content_type, ext)
    raise RuntimeError("STORAGE_BACKEND must be either 'minio' or 'azure'")


def put_review_file(file_bytes: bytes, content_type: str, ext: str):
    """Use the configured storage backend for review photos and videos."""
    folder = "videos" if content_type.startswith("video/") else "images"
    key = f"reviews/{folder}/{uuid.uuid4().hex}{ext}"
    if STORAGE_BACKEND == "azure":
        return key, _put_azure_blob(file_bytes, content_type, ext, key=key)
    if STORAGE_BACKEND == "minio":
        return key, _put_minio_object(file_bytes, content_type, ext, key=key)
    raise StorageConfigurationError("STORAGE_BACKEND must be either 'minio' or 'azure'")


def _validate_review_key(key):
    # Keep the original flat review paths readable for existing uploads.
    if not re.fullmatch(
        r"reviews/(?:(?:images/)?[a-f0-9]{32}\.(?:jpg|png|webp|gif)"
        r"|(?:videos/)?[a-f0-9]{32}\.(?:mp4|webm))", key,
    ):
        raise ValueError("Invalid review media key")


def delete_review_file(key: str):
    _validate_review_key(key)
    if STORAGE_BACKEND == "azure":
        _azure_container_client().get_blob_client(key).delete_blob()
    elif STORAGE_BACKEND == "minio":
        _minio_client().delete_object(Bucket=MINIO_BUCKET, Key=key)
    else:
        raise StorageConfigurationError("STORAGE_BACKEND must be either 'minio' or 'azure'")


class InvalidMediaRange(ValueError):
    def __init__(self, total):
        self.total = total
        super().__init__("Invalid media byte range")


def _review_media_range(total, range_header):
    start, end = 0, total - 1
    if range_header:
        match = re.fullmatch(r"bytes=(\d*)-(\d*)", range_header.strip())
        if not match or not any(match.groups()) or total == 0:
            raise InvalidMediaRange(total)
        first, last = match.groups()
        if first:
            start = int(first)
            end = min(int(last), total - 1) if last else total - 1
        else:
            suffix = int(last)
            if suffix == 0:
                raise InvalidMediaRange(total)
            start = max(0, total - suffix)
        if start >= total or end < start:
            raise InvalidMediaRange(total)
    return start, end


def get_review_media(key: str, range_header=None):
    """Stream review media from either backend, including video byte ranges."""
    _validate_review_key(key)
    if STORAGE_BACKEND == "minio":
        client = _minio_client()
        properties = client.head_object(Bucket=MINIO_BUCKET, Key=key)
        total = properties["ContentLength"]
        start, end = _review_media_range(total, range_header)
        options = {"Range": f"bytes={start}-{end}"} if range_header else {}
        download = client.get_object(Bucket=MINIO_BUCKET, Key=key, **options)

        def chunks():
            try:
                yield from download["Body"].iter_chunks(chunk_size=64 * 1024)
            finally:
                download["Body"].close()

        return chunks(), properties.get("ContentType") or "application/octet-stream", total, start, end
    if STORAGE_BACKEND != "azure":
        raise StorageConfigurationError("STORAGE_BACKEND must be either 'minio' or 'azure'")
    blob = _azure_container_client().get_blob_client(key)
    properties = blob.get_blob_properties()
    total = properties.size
    content_type = properties.content_settings.content_type or "application/octet-stream"
    start, end = _review_media_range(total, range_header)
    if range_header:
        download = blob.download_blob(offset=start, length=end - start + 1)
    else:
        download = blob.download_blob()
    return download.chunks(), content_type, total, start, end
