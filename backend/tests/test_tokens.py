"""Token compatibility and rejection properties across the JWT dependency change."""
import base64
import hashlib
import hmac
import json
import time

import jwt
import pytest

from app import security


def legacy_token(claims, secret=None):
    """Construct the HS256 wire format previously produced by python-jose."""
    def encode(value):
        return base64.urlsafe_b64encode(json.dumps(value, separators=(",", ":")).encode()).rstrip(b"=")

    message = encode({"alg": "HS256", "typ": "JWT"}) + b"." + encode(claims)
    signature = hmac.new((secret or security.SECRET_KEY).encode(), message, hashlib.sha256).digest()
    return (message + b"." + base64.urlsafe_b64encode(signature).rstrip(b"=")).decode()


def test_existing_hs256_token_remains_valid():
    token = legacy_token({"sub": "legacy@example.com", "exp": int(time.time()) + 60})
    assert security.decode_token(token)["sub"] == "legacy@example.com"


def test_new_token_keeps_hs256_wire_signature():
    token = security.create_access_token({"sub": "new@example.com"})
    header, payload, signature = token.split(".")
    expected = hmac.new(security.SECRET_KEY.encode(), f"{header}.{payload}".encode(), hashlib.sha256).digest()
    assert hmac.compare_digest(base64.urlsafe_b64decode(signature + "=" * (-len(signature) % 4)), expected)


def test_expired_legacy_token_is_rejected():
    with pytest.raises(jwt.ExpiredSignatureError):
        security.decode_token(legacy_token({"sub": "old@example.com", "exp": int(time.time()) - 60}))


def test_wrong_signature_is_rejected():
    with pytest.raises(jwt.InvalidSignatureError):
        security.decode_token(legacy_token({"sub": "wrong@example.com"}, secret="different-test-key-" * 3))


def test_algorithm_cannot_be_selected_by_token():
    token = jwt.encode({"sub": "attacker@example.com"}, security.SECRET_KEY, algorithm="HS512")
    with pytest.raises(jwt.InvalidAlgorithmError):
        security.decode_token(token)
