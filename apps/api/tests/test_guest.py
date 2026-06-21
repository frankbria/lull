"""Guest generation gating (FR-A2): one free /tts per X-Guest-Id, then sign-up required.
Authenticated users are never blocked at launch (entitlements are free)."""

from __future__ import annotations

import uuid

from lull_api.audio import StubAudioSource
from lull_api.main import app, get_source


def _tts(client, **headers):
    return client.post("/tts", json={"text": "rest now"}, headers=headers)


def _stub_source(client):
    app.dependency_overrides[get_source] = lambda: StubAudioSource()
    return client


def test_guest_gets_one_free_then_blocked(client):
    _stub_source(client)
    try:
        guest = str(uuid.uuid4())
        assert _tts(client, **{"X-Guest-Id": guest}).status_code == 200  # free one
        assert _tts(client, **{"X-Guest-Id": guest}).status_code == 401  # must sign up now
    finally:
        app.dependency_overrides.pop(get_source, None)


def test_distinct_guests_each_get_a_free_generation(client):
    _stub_source(client)
    try:
        assert _tts(client, **{"X-Guest-Id": str(uuid.uuid4())}).status_code == 200
        assert _tts(client, **{"X-Guest-Id": str(uuid.uuid4())}).status_code == 200
    finally:
        app.dependency_overrides.pop(get_source, None)


def test_no_identity_at_all_is_401(client):
    _stub_source(client)
    try:
        assert _tts(client).status_code == 401  # no token, no guest id
    finally:
        app.dependency_overrides.pop(get_source, None)


def test_bad_guest_id_is_422(client):
    _stub_source(client)
    try:
        assert _tts(client, **{"X-Guest-Id": "not-a-uuid"}).status_code == 422
    finally:
        app.dependency_overrides.pop(get_source, None)


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
        app.dependency_overrides.pop(get_source, None)
