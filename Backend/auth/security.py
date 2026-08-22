# auth/security.py

import hashlib
import hmac
import os
import secrets
from datetime import datetime, timedelta, timezone

import jwt

_PBKDF2_ALGO = "sha256"
_PBKDF2_ITERATIONS = 200_000
_SALT_BYTES = 16


def hash_password(password: str) -> tuple[str, str]:
    """Return ``(hash_hex, salt_hex)`` for a plaintext password."""
    salt = secrets.token_bytes(_SALT_BYTES)
    dk = hashlib.pbkdf2_hmac(_PBKDF2_ALGO, password.encode("utf-8"), salt, _PBKDF2_ITERATIONS)
    return dk.hex(), salt.hex()


def verify_password(password: str, pwd_hash: str, pwd_salt: str) -> bool:
    """Constant-time check of a plaintext password against a stored hash."""
    if not pwd_hash or not pwd_salt:
        return False
    try:
        salt = bytes.fromhex(pwd_salt)
    except (ValueError, TypeError):
        return False
    dk = hashlib.pbkdf2_hmac(_PBKDF2_ALGO, password.encode("utf-8"), salt, _PBKDF2_ITERATIONS)
    return hmac.compare_digest(dk.hex(), pwd_hash)


def _secret() -> str:
    return os.getenv("JWT_SECRET", "dev-insecure-change-me")


def _expire_minutes() -> int:
    try:
        return int(os.getenv("JWT_EXPIRE_MINUTES", "10080"))
    except (ValueError, TypeError):
        return 10080


def create_token(user_id: str) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "iat": now,
        "exp": now + timedelta(minutes=_expire_minutes()),
    }
    return jwt.encode(payload, _secret(), algorithm="HS256")


def decode_token(token: str) -> dict:
    """Decode a JWT, raising ``jwt.PyJWTError`` (or a subclass) on any problem."""
    return jwt.decode(token, _secret(), algorithms=["HS256"])
