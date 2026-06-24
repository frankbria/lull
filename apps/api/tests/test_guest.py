"""Guest generation gating (FR-A2): one free /tts per server-issued guest token, then sign-up
required. Authenticated users are never blocked at launch (entitlements are free)."""

from __future__ import annotations

from lull_api.audio import StubAudioSource
from lull_api.main import app, get_source_factory


def _guest_token(client) -> str:
    return client.post("/auth/guest").json()["guest_token"]


def _tts(client, **headers):
    return client.post("/tts", json={"text": "rest now"}, headers=headers)


def _stub_source(client):
    app.dependency_overrides[get_source_factory] = lambda: (lambda v=None: StubAudioSource())
    return client


def test_guest_gets_one_free_then_blocked(client):
    _stub_source(client)
    try:
        token = _guest_token(client)
        assert _tts(client, **{"X-Guest-Token": token}).status_code == 200  # free one
        assert _tts(client, **{"X-Guest-Token": token}).status_code == 401  # must sign up now
    finally:
        app.dependency_overrides.pop(get_source_factory, None)


def test_distinct_guests_each_get_a_free_generation(client):
    _stub_source(client)
    try:
        assert _tts(client, **{"X-Guest-Token": _guest_token(client)}).status_code == 200
        assert _tts(client, **{"X-Guest-Token": _guest_token(client)}).status_code == 200
    finally:
        app.dependency_overrides.pop(get_source_factory, None)


def test_no_identity_at_all_is_401(client):
    _stub_source(client)
    try:
        assert _tts(client).status_code == 401  # no token, no guest token
    finally:
        app.dependency_overrides.pop(get_source_factory, None)


def test_forged_guest_token_is_401(client):
    _stub_source(client)
    try:
        assert _tts(client, **{"X-Guest-Token": "not-a-real-token"}).status_code == 401
    finally:
        app.dependency_overrides.pop(get_source_factory, None)


def test_failed_synthesis_does_not_burn_the_free_generation(client):
    """A retryable upstream failure must NOT consume the guest's one free generation."""
    from lull_api.audio import AudioSourceError

    class _FlakySource(StubAudioSource):
        async def synthesize(self, text: str) -> bytes:
            raise AudioSourceError(status_code=504, message="upstream timeout", retryable=True)

    app.dependency_overrides[get_source_factory] = lambda: (lambda v=None: _FlakySource())
    try:
        token = _guest_token(client)
        assert _tts(client, **{"X-Guest-Token": token}).status_code == 504  # render failed
        # Credit untouched → switching to a working source still grants the free generation.
        app.dependency_overrides[get_source_factory] = lambda: (lambda v=None: StubAudioSource())
        assert _tts(client, **{"X-Guest-Token": token}).status_code == 200
    finally:
        app.dependency_overrides.pop(get_source_factory, None)


def test_authenticated_user_is_never_blocked(client):
    _stub_source(client)
    try:
        signup = client.post(
            "/auth/signup",
            json={"email": "gen@example.com", "password": "hunter2hunter", "age_confirmed": True},
        )
        token = signup.json()["access_token"]
        auth = {"Authorization": f"Bearer {token}"}
        for _ in range(3):  # well past the guest free limit
            assert _tts(client, **auth).status_code == 200
    finally:
        app.dependency_overrides.pop(get_source_factory, None)
