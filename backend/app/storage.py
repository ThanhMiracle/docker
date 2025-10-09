import os, uuid, json
from minio import Minio
from io import BytesIO
MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "minio:9000")
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "minioadmin")
MINIO_BUCKET = os.getenv("MINIO_BUCKET", "uploads")
MINIO_SECURE = os.getenv("MINIO_SECURE", "false").lower() == "true"
MINIO_PUBLIC_URL = os.getenv("MINIO_PUBLIC_URL", "http://localhost:9000")
client = Minio(MINIO_ENDPOINT, access_key=MINIO_ACCESS_KEY, secret_key=MINIO_SECRET_KEY, secure=MINIO_SECURE)
def ensure_bucket_public():
    if not client.bucket_exists(MINIO_BUCKET):
        client.make_bucket(MINIO_BUCKET)
    policy = {"Version":"2012-10-17","Statement":[{"Effect":"Allow","Principal":{"AWS":["*"]},"Action":["s3:GetObject"],"Resource":[f"arn:aws:s3:::{MINIO_BUCKET}/*"]}]}
    client.set_bucket_policy(MINIO_BUCKET, json.dumps(policy))
def put_file(file_bytes: bytes, content_type: str, ext: str = "") -> str:
    ensure_bucket_public()
    key = f"{uuid.uuid4().hex}{ext if ext else ''}"
    client.put_object(MINIO_BUCKET, key, data=BytesIO(file_bytes), length=len(file_bytes), content_type=content_type)
    return f"{MINIO_PUBLIC_URL}/{MINIO_BUCKET}/{key}"
