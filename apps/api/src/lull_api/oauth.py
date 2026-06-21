"""Provider id_token verification (Google + Apple).

Native mobile sign-in (Expo/RN) gets an `id_token` from the provider and posts it here; the
backend verifies the signature against the provider's JWKS plus audience/issuer/exp, then trusts
the email claim. No redirect/auth-code flow — that lives in the provider SDK on-device.

ponytail: a verifier seam (one dependency, like get_source) over PyJWT's JWKS client, not an OAuth
framework. The seam exists so tests can inject a verifier backed by a real test keypair (real
RS256 verification, test issuer key) instead of reaching out to Google/Apple.
"""

from __future__ import annotations

from dataclasses import dataclass

import jwt
from jwt import PyJWKClient

from .config import settings


class OAuthError(Exception):
    """id_token failed verification, or the provider isn't configured."""


@dataclass(frozen=True)
class VerifiedIdentity:
    email: str
    provider: str


@dataclass(frozen=True)
class _Provider:
    jwks_uri: str
    issuers: tuple[str, ...]


_PROVIDERS: dict[str, _Provider] = {
    "google": _Provider(
        jwks_uri="https://www.googleapis.com/oauth2/v3/certs",
        issuers=("https://accounts.google.com", "accounts.google.com"),
    ),
    "apple": _Provider(
        jwks_uri="https://appleid.apple.com/auth/keys",
        issuers=("https://appleid.apple.com",),
    ),
}


def _audiences(provider: str) -> list[str]:
    return {"google": settings.google_client_ids, "apple": settings.apple_client_ids}[provider]


class OAuthVerifier:
    def __init__(self) -> None:
        self._clients: dict[str, PyJWKClient] = {}

    def _signing_key(self, provider: str, id_token: str):
        client = self._clients.get(provider)
        if client is None:
            client = PyJWKClient(_PROVIDERS[provider].jwks_uri)
            self._clients[provider] = client
        return client.get_signing_key_from_jwt(id_token).key

    def verify(self, provider: str, id_token: str) -> VerifiedIdentity:
        provider_cfg = _PROVIDERS.get(provider)
        if provider_cfg is None:
            raise OAuthError(f"unknown provider: {provider}")
        audiences = _audiences(provider)
        if not audiences:
            raise OAuthError(f"{provider} OAuth not configured (no client ids)")
        try:
            key = self._signing_key(provider, id_token)
            claims = jwt.decode(
                id_token,
                key,
                algorithms=["RS256"],
                audience=audiences,
                issuer=list(provider_cfg.issuers),
            )
        except jwt.InvalidTokenError as exc:
            raise OAuthError(f"invalid id_token: {exc}") from exc

        email = claims.get("email")
        if not email:
            raise OAuthError("id_token has no email claim")
        # Providers send email_verified as bool or the string "true".
        if str(claims.get("email_verified", "true")).lower() != "true":
            raise OAuthError("provider email is not verified")
        return VerifiedIdentity(email=email.lower(), provider=provider)


_verifier = OAuthVerifier()


def get_oauth_verifier() -> OAuthVerifier:
    """FastAPI dependency. Overridden in tests with a verifier backed by a test keypair."""
    return _verifier
