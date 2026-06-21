"""Password hashing (argon2) + session JWT (HS256).

ponytail: a hashing context + two JWT helpers, not an auth framework. Upgrade path — add refresh
tokens / key rotation only when sessions need revocation.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import jwt
from passlib.context import CryptContext

from .config import settings

_pwd = CryptContext(schemes=["argon2"], deprecated="auto")

ALGORITHM = "HS256"


def hash_password(password: str) -> str:
    return _pwd.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return _pwd.verify(password, password_hash)


def create_access_token(user_id: uuid.UUID) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "iat": now,
        "exp": now + timedelta(minutes=settings.jwt_expire_minutes),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=ALGORITHM)


def decode_access_token(token: str) -> uuid.UUID:
    """Return the user id from a valid token, or raise jwt.InvalidTokenError."""
    payload = jwt.decode(token, settings.jwt_secret, algorithms=[ALGORITHM])
    if payload.get("typ") == "guest":
        raise jwt.InvalidTokenError("guest token is not a user session")
    return uuid.UUID(payload["sub"])


def create_guest_token() -> tuple[str, uuid.UUID]:
    """Mint a signed, server-issued guest identity (FR-A2). Integrity-protected so a client can't
    fabricate guest ids to dodge the free-generation limit. Returns (token, guest_id)."""
    guest_id = uuid.uuid4()
    now = datetime.now(timezone.utc)
    token = jwt.encode(
        {
            "sub": str(guest_id),
            "typ": "guest",
            "iat": now,
            "exp": now + timedelta(minutes=settings.jwt_expire_minutes),
        },
        settings.jwt_secret,
        algorithm=ALGORITHM,
    )
    return token, guest_id


def decode_guest_token(token: str) -> uuid.UUID:
    """Return the guest id from a valid guest token, or raise jwt.InvalidTokenError."""
    payload = jwt.decode(token, settings.jwt_secret, algorithms=[ALGORITHM])
    if payload.get("typ") != "guest":
        raise jwt.InvalidTokenError("not a guest token")
    return uuid.UUID(payload["sub"])
