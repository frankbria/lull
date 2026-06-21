"""OAuth id_token verification.

No mocking of our verifier: we mint a real RSA keypair, sign real RS256 id_tokens with it, and
inject a verifier that uses the test public key (standing in for Google's signing key). The
verification path — signature, audience, issuer, exp, email_verified — runs for real.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from lull_api.config import settings
from lull_api.main import app
from lull_api.oauth import OAuthVerifier, get_oauth_verifier

AUDIENCE = "test-client.apps.googleusercontent.com"
ISSUER = "https://accounts.google.com"


@pytest.fixture(scope="module")
def keypair():
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    private_pem = key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    return private_pem, key.public_key()


class _TestVerifier(OAuthVerifier):
    def __init__(self, public_key):
        super().__init__()
        self._public_key = public_key

    def _signing_key(self, provider, id_token):  # type: ignore[override]
        return self._public_key


@pytest.fixture
def oauth_client(client, keypair, monkeypatch):
    """client fixture (transactional DB) + Google audience configured + injected test verifier."""
    monkeypatch.setattr(settings, "google_client_ids", [AUDIENCE])
    app.dependency_overrides[get_oauth_verifier] = lambda: _TestVerifier(keypair[1])
    return client


def _id_token(
    keypair,
    *,
    email="oauth@example.com",
    aud=AUDIENCE,
    iss=ISSUER,
    email_verified=True,
    exp_delta=timedelta(hours=1),
):
    private_pem = keypair[0]
    now = datetime.now(timezone.utc)
    return jwt.encode(
        {
            "iss": iss,
            "aud": aud,
            "email": email,
            "email_verified": email_verified,
            "iat": now,
            "exp": now + exp_delta,
            "sub": "provider-subject-123",
        },
        private_pem,
        algorithm="RS256",
        headers={"kid": "test-key"},
    )


def test_oauth_creates_account_and_returns_token(oauth_client, keypair):
    r = oauth_client.post(
        "/auth/oauth/google",
        json={"id_token": _id_token(keypair), "age_confirmed": True},
    )
    assert r.status_code == 200
    token = r.json()["access_token"]
    me = oauth_client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.json()["email"] == "oauth@example.com"
    assert me.json()["age_verified"] is True


def test_oauth_new_account_requires_age_confirmation(oauth_client, keypair):
    r = oauth_client.post(
        "/auth/oauth/google",
        json={"id_token": _id_token(keypair), "age_confirmed": False},
    )
    assert r.status_code == 422


def test_oauth_returning_user_skips_age_gate(oauth_client, keypair):
    first = oauth_client.post(
        "/auth/oauth/google", json={"id_token": _id_token(keypair), "age_confirmed": True}
    )
    assert first.status_code == 200
    # Second sign-in (existing account) succeeds even without re-attesting age.
    again = oauth_client.post(
        "/auth/oauth/google", json={"id_token": _id_token(keypair), "age_confirmed": False}
    )
    assert again.status_code == 200


def test_oauth_rejects_wrong_audience(oauth_client, keypair):
    r = oauth_client.post(
        "/auth/oauth/google",
        json={"id_token": _id_token(keypair, aud="someone-else"), "age_confirmed": True},
    )
    assert r.status_code == 401


def test_oauth_rejects_expired_token(oauth_client, keypair):
    r = oauth_client.post(
        "/auth/oauth/google",
        json={"id_token": _id_token(keypair, exp_delta=timedelta(hours=-1)), "age_confirmed": True},
    )
    assert r.status_code == 401


def test_oauth_rejects_unverified_email(oauth_client, keypair):
    r = oauth_client.post(
        "/auth/oauth/google",
        json={"id_token": _id_token(keypair, email_verified=False), "age_confirmed": True},
    )
    assert r.status_code == 401


def test_oauth_unknown_provider_is_401(oauth_client, keypair):
    r = oauth_client.post(
        "/auth/oauth/facebook",
        json={"id_token": _id_token(keypair), "age_confirmed": True},
    )
    assert r.status_code == 401
