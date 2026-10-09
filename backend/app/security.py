import os
import base64
import hashlib
import hmac
import json
import time
from datetime import datetime, timedelta
from typing import Optional
from cryptography.fernet import Fernet, InvalidToken
from jose import jwt
from passlib.context import CryptContext
SECRET_KEY = os.getenv("JWT_SECRET", "dev-secret-key-change-me")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", "120"))
pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")
def verify_password(plain_password, hashed_password): return pwd_context.verify(plain_password, hashed_password)
def get_password_hash(password): return pwd_context.hash(password)
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
def decode_token(token: str): return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])

REGISTRATION_TOKEN_PREFIX = "registration-v1."
REGISTRATION_TOKEN_TTL = 30 * 60


def _registration_cipher():
    # Separate registration encryption from access-token signing, using the
    # shared server secret so links work across workers and restarts.
    key = hmac.new(
        SECRET_KEY.encode(), b"account-registration-v1", hashlib.sha256
    ).digest()
    return Fernet(base64.urlsafe_b64encode(key))


def create_registration_token(name: str, email: str, password: str):
    payload = {
        "name": name.strip(),
        "email": email.strip().lower(),
        "hashed_password": get_password_hash(password),
    }
    encrypted = _registration_cipher().encrypt(json.dumps(payload).encode())
    return REGISTRATION_TOKEN_PREFIX + encrypted.decode()


def decode_registration_token(token: str):
    if not token.startswith(REGISTRATION_TOKEN_PREFIX):
        return None, "invalid"
    encrypted = token[len(REGISTRATION_TOKEN_PREFIX):].encode()
    cipher = _registration_cipher()
    try:
        payload = json.loads(cipher.decrypt(encrypted, ttl=REGISTRATION_TOKEN_TTL))
    except InvalidToken:
        try:
            issued_at = cipher.extract_timestamp(encrypted)
        except InvalidToken:
            return None, "invalid"
        if issued_at + REGISTRATION_TOKEN_TTL < time.time():
            return None, "expired"
        return None, "invalid"
    except (ValueError, UnicodeDecodeError):
        return None, "invalid"
    if not isinstance(payload, dict) or any(
        not isinstance(payload.get(field), str) or not payload[field]
        for field in ("name", "email", "hashed_password")
    ):
        return None, "invalid"
    return payload, None
