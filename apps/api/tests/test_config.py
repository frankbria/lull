"""Settings safety: a deployed environment must not silently sign tokens with the public default
JWT secret."""

from __future__ import annotations

import pytest

from lull_api.config import _DEFAULT_JWT_SECRET, Settings


def test_default_secret_allowed_in_dev():
    s = Settings(environment="development", jwt_secret=_DEFAULT_JWT_SECRET)
    assert s.jwt_secret == _DEFAULT_JWT_SECRET


def test_default_secret_rejected_in_production():
    with pytest.raises(ValueError):
        Settings(environment="production", jwt_secret=_DEFAULT_JWT_SECRET)


def test_short_secret_rejected_in_production():
    with pytest.raises(ValueError):
        Settings(environment="production", jwt_secret="x")  # passes the default check, too short


def test_real_secret_accepted_in_production():
    s = Settings(environment="production", jwt_secret="a-real-long-random-production-secret-value")
    assert s.environment == "production"
