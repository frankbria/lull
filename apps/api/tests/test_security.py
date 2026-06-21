"""Password hashing + session JWT round-trips."""

from __future__ import annotations

import uuid

import jwt
import pytest

from lull_api.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)


def test_password_hash_roundtrip():
    h = hash_password("correct horse battery staple")
    assert h != "correct horse battery staple"  # not stored in clear
    assert h.startswith("$argon2")
    assert verify_password("correct horse battery staple", h) is True
    assert verify_password("wrong", h) is False


def test_access_token_roundtrip():
    uid = uuid.uuid4()
    token = create_access_token(uid)
    assert decode_access_token(token) == uid


def test_decode_rejects_tampered_token():
    token = create_access_token(uuid.uuid4())
    with pytest.raises(jwt.InvalidTokenError):
        decode_access_token(token + "x")
