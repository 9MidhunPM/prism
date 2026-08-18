"""Password and signed-session helpers for authenticated PRISM accounts."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import time


def hash_password(password: str) -> str:
    salt = os.urandom(16)
    derived = hashlib.scrypt(password.encode(), salt=salt, n=2**14, r=8, p=1)
    return f"scrypt${base64.urlsafe_b64encode(salt).decode()}${base64.urlsafe_b64encode(derived).decode()}"


def verify_password(password: str, encoded: str) -> bool:
    try:
        algorithm, salt_encoded, hash_encoded = encoded.split("$", 2)
        if algorithm != "scrypt":
            return False
        salt = base64.urlsafe_b64decode(salt_encoded)
        expected = base64.urlsafe_b64decode(hash_encoded)
    except (ValueError, UnicodeDecodeError):
        return False
    actual = hashlib.scrypt(password.encode(), salt=salt, n=2**14, r=8, p=1)
    return hmac.compare_digest(actual, expected)


def random_token() -> str:
    return base64.urlsafe_b64encode(os.urandom(32)).decode().rstrip("=")


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def create_session(account_id: str, secret: str, ttl_seconds: int, role: str = "teacher") -> str:
    payload = base64.urlsafe_b64encode(json.dumps({"sub": account_id, "role": role, "exp": int(time.time()) + ttl_seconds}).encode()).decode().rstrip("=")
    signature = hmac.new(secret.encode(), payload.encode(), hashlib.sha256).hexdigest()
    return f"{payload}.{signature}"


def read_session(token: str | None, secret: str) -> str | None:
    data = read_session_data(token, secret)
    return data["sub"] if data else None


def read_session_data(token: str | None, secret: str) -> dict[str, str] | None:
    if not token or "." not in token:
        return None
    payload, signature = token.rsplit(".", 1)
    expected = hmac.new(secret.encode(), payload.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(signature, expected):
        return None
    try:
        data = json.loads(base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4)))
        if not isinstance(data["sub"], str) or data.get("role") not in {"teacher", "student"} or data["exp"] < time.time():
            return None
        return {"sub": data["sub"], "role": data["role"]}
    except (KeyError, TypeError, ValueError, json.JSONDecodeError):
        return None
