import os
import uuid
import json
from urllib.parse import quote

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError


AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
AWS_S3_BUCKET = os.getenv("AWS_S3_BUCKET")
AWS_S3_PUBLIC_URL = os.getenv("AWS_S3_PUBLIC_URL")
AWS_S3_ENDPOINT_URL = os.getenv("AWS_S3_ENDPOINT_URL")
AWS_S3_AUTO_CREATE_BUCKET = os.getenv("AWS_S3_AUTO_CREATE_BUCKET", "").lower() in {
    "1",
    "true",
    "yes",
}


def _client():
    # boto3 automatically uses AWS_ACCESS_KEY_ID/AWS_SECRET_ACCESS_KEY when
    # provided, or the ECS/EC2 task role in production.
    return boto3.client(
        "s3",
        region_name=AWS_REGION,
        endpoint_url=AWS_S3_ENDPOINT_URL,
        config=Config(s3={"addressing_style": "path"})
        if AWS_S3_ENDPOINT_URL
        else None,
    )


def _ensure_local_bucket(client):
    if not AWS_S3_AUTO_CREATE_BUCKET:
        return
    try:
        client.head_bucket(Bucket=AWS_S3_BUCKET)
    except ClientError:
        client.create_bucket(Bucket=AWS_S3_BUCKET)

    policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": "*",
                "Action": "s3:GetObject",
                "Resource": f"arn:aws:s3:::{AWS_S3_BUCKET}/*",
            }
        ],
    }
    client.put_bucket_policy(Bucket=AWS_S3_BUCKET, Policy=json.dumps(policy))


def _object_url(key: str) -> str:
    encoded_key = quote(key, safe="/")
    if AWS_S3_PUBLIC_URL:
        return f"{AWS_S3_PUBLIC_URL.rstrip('/')}/{encoded_key}"
    if AWS_REGION == "us-east-1":
        return f"https://{AWS_S3_BUCKET}.s3.amazonaws.com/{encoded_key}"
    return f"https://{AWS_S3_BUCKET}.s3.{AWS_REGION}.amazonaws.com/{encoded_key}"


def put_file(file_bytes: bytes, content_type: str, ext: str = "") -> str:
    if not AWS_S3_BUCKET:
        raise RuntimeError("AWS_S3_BUCKET is required")

    key = f"{uuid.uuid4().hex}{ext}"
    client = _client()
    _ensure_local_bucket(client)
    client.put_object(
        Bucket=AWS_S3_BUCKET,
        Key=key,
        Body=file_bytes,
        ContentType=content_type,
    )
    return _object_url(key)
