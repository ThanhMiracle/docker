import os, uuid, json
from urllib.parse import urlparse
from io import BytesIO
from minio import Minio

# ---- Env & helpers ---------------------------------------------------------

def _as_bool(v: str, default=False) -> bool:
    if v is None:
        return default
    v = v.strip().lower()
    return v in ("1", "true", "yes", "y", "on")

def _normalize_minio_endpoint(endpoint_raw: str, secure_flag: bool):
    """
    Chấp nhận:
      - 'minio:9000'
      - 'http://minio:9000'
      - 'https://minio:9000'
    Trả về (endpoint_no_scheme, secure_bool).
    Không cho phép có path.
    """
    if "://" in endpoint_raw:
        p = urlparse(endpoint_raw)
        if p.path not in ("", "/"):
            raise ValueError("MINIO_ENDPOINT must not include a path")
        host = p.hostname
        port = f":{p.port}" if p.port else ""
        endpoint = f"{host}{port}"
        secure = (p.scheme == "https")
        return endpoint, secure
    else:
        # Không có scheme -> dùng secure_flag để quyết định http/https
        p = urlparse(("https://" if secure_flag else "http://") + endpoint_raw)
        if p.path not in ("", "/"):
            raise ValueError("MINIO_ENDPOINT must not include a path")
        host = p.hostname
        port = f":{p.port}" if p.port else ""
        endpoint = f"{host}{port}"
        return endpoint, secure_flag

def _url_join(a: str, b: str) -> str:
    return a.rstrip("/") + "/" + b.lstrip("/")

# ---- Read env --------------------------------------------------------------

MINIO_ENDPOINT_RAW = os.getenv("MINIO_ENDPOINT", "minio:9000")  # có thể là 'minio:9000' hoặc 'http://minio:9000'
MINIO_ACCESS_KEY   = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
MINIO_SECRET_KEY   = os.getenv("MINIO_SECRET_KEY", "minioadmin")
MINIO_BUCKET       = os.getenv("MINIO_BUCKET", "uploads")
MINIO_SECURE_FLAG  = _as_bool(os.getenv("MINIO_SECURE", "false"), default=False)

MINIO_PUBLIC_URL   = os.getenv("MINIO_PUBLIC_URL")  # ví dụ: http://<PUBLIC_IP>/minio-public

# Chuẩn hoá endpoint cho Minio client
MINIO_ENDPOINT, MINIO_SECURE_BOOL = _normalize_minio_endpoint(MINIO_ENDPOINT_RAW, MINIO_SECURE_FLAG)

# ---- Minio client ----------------------------------------------------------

client = Minio(
    MINIO_ENDPOINT,
    access_key=MINIO_ACCESS_KEY,
    secret_key=MINIO_SECRET_KEY,
    secure=MINIO_SECURE_BOOL,
)

# ---- Bucket & upload helpers -----------------------------------------------

def ensure_bucket_public():
    if not client.bucket_exists(MINIO_BUCKET):
        client.make_bucket(MINIO_BUCKET)
    # Public-read policy (chỉ nên dùng nếu bạn thật sự muốn public-read)
    policy = {
        "Version":"2012-10-17",
        "Statement":[
            {
                "Effect":"Allow",
                "Principal":{"AWS":["*"]},
                "Action":["s3:GetObject"],
                "Resource":[f"arn:aws:s3:::{MINIO_BUCKET}/*"]
            }
        ]
    }
    client.set_bucket_policy(MINIO_BUCKET, json.dumps(policy))

def put_file(file_bytes: bytes, content_type: str, ext: str = "") -> str:
    ensure_bucket_public()
    key = f"{uuid.uuid4().hex}{ext if ext else ''}"
    client.put_object(
        MINIO_BUCKET,
        key,
        data=BytesIO(file_bytes),
        length=len(file_bytes),
        content_type=content_type
    )
    # URL public: nếu bạn reverse proxy MinIO qua /minio-public,
    # MINIO_PUBLIC_URL nên là 'http://<PUBLIC_IP>/minio-public'
    return _url_join(MINIO_PUBLIC_URL, f"{MINIO_BUCKET}/{key}")
