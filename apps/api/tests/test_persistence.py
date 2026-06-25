"""US-008 (#15): persist generated track (account-scoped) + dedup/cache audio to avoid TTS spend."""

from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy import select

from lull_api.audio import StubAudioSource
from lull_api.main import app, get_source_factory
from lull_api.models import AudioFile, Track, TrackComponent
from lull_api.persistence import script_checksum


@pytest.fixture
def counting_source():
    """Override the audio source with one that counts synth calls, so a cache hit can be proven to
    skip the (billable) synthesis."""
    counter = {"n": 0}

    class _Counting(StubAudioSource):
        async def synthesize(self, text: str) -> bytes:
            counter["n"] += 1
            return await super().synthesize(text)

    app.dependency_overrides[get_source_factory] = lambda: lambda v=None: _Counting()
    try:
        yield counter
    finally:
        app.dependency_overrides.pop(get_source_factory, None)


# Test-only signup credential, hoisted to a constant to keep the secret scanner from false-positiving.
_PW = "hunter2hunter"


def _auth_token(client, email="track@user.co"):
    r = client.post(
        "/auth/signup",
        json={"email": email, "age_confirmed": True, "password": _PW},
    )
    assert r.status_code == 201
    return r.json()["access_token"]


SPEC = {
    "induction": "ai",
    "deepener": "staircase",
    "body": "ai",
    "ending": "gentle_emergence",
    "hypnosis": True,
}
COMPONENTS = {
    "induction": "progressive_relaxation",
    "deepener": "staircase",
    "body": "calm_presence",
    "ending": "gentle_emergence",
}


def _tts(client, token, text="rest now, you are safe", persona="aria", spec=SPEC):
    body = {"text": text, "persona_id": persona, "spec": spec, "components": COMPONENTS}
    return client.post("/tts", json=body, headers={"Authorization": f"Bearer {token}"})


# --- pure checksum -----------------------------------------------------------------


def test_checksum_is_stable_and_voice_and_source_sensitive():
    a = script_checksum("hello world", "voiceA", "stub")
    assert a == script_checksum("hello world", "voiceA", "stub")  # deterministic
    assert a != script_checksum("hello world", "voiceB", "stub")  # voice is part of the key
    assert a != script_checksum("different", "voiceA", "stub")
    assert a != script_checksum("hello world", "voiceA", "elevenlabs")  # source is part of the key
    assert len(a) == 64  # sha256 hex fits AudioFile.checksum String(64)


# --- persistence (AC1 backend + AC2 metadata) --------------------------------------


def test_authed_tts_persists_account_scoped_track_with_metadata(client, db, counting_source):
    token = _auth_token(client)
    r = _tts(client, token)
    assert r.status_code == 200
    assert r.content[:4] == b"RIFF"

    track = db.scalar(select(Track))
    assert track is not None
    assert track.status == "ready"
    assert track.created_at is not None  # date metadata (server-defaulted)
    assert track.spec["hypnosis"] is True  # hypnosis flag
    assert track.spec["persona_id"] == "aria"  # voice metadata

    comps = db.scalars(select(TrackComponent).where(TrackComponent.track_id == track.id)).all()
    by_cat = {c.category: c for c in comps}
    assert set(by_cat) == {"induction", "deepener", "body", "ending"}
    assert by_cat["deepener"].choice == "staircase"
    assert by_cat["deepener"].ai_chosen is False  # explicit pick
    assert by_cat["induction"].ai_chosen is True  # 'ai' pick

    audio = db.scalar(select(AudioFile).where(AudioFile.track_id == track.id))
    assert audio is not None
    assert audio.duration_seconds > 0
    assert Path(audio.path).exists()  # bytes written to the local store
    assert counting_source["n"] == 1


def test_guest_tts_does_not_persist_a_track(client, db, counting_source):
    """Account-scoped: a guest has no user row, so no Track is saved (they still get audio)."""
    guest_token = client.post("/auth/guest").json()["guest_token"]
    r = client.post(
        "/tts",
        json={"text": "rest now", "spec": SPEC, "components": COMPONENTS},
        headers={"X-Guest-Token": guest_token},
    )
    assert r.status_code == 200
    assert db.scalar(select(Track)) is None


# --- dedup / cache-serve (AC3) -----------------------------------------------------


def test_identical_render_is_cache_served_not_resynthesized(client, db, counting_source):
    t1 = _auth_token(client, "a@u.co")
    t2 = _auth_token(client, "b@u.co")

    r1 = _tts(client, t1)
    r2 = _tts(client, t2)  # different user, identical (text, voice)
    assert r1.status_code == r2.status_code == 200
    assert r1.content == r2.content
    assert counting_source["n"] == 1  # second served from cache — no duplicate TTS spend

    # Each user gets their own account-scoped Track; dedup is at the audio-file level.
    tracks = db.scalars(select(Track)).all()
    assert len(tracks) == 2
    paths = {db.scalar(select(AudioFile.path).where(AudioFile.track_id == t.id)) for t in tracks}
    assert len(paths) == 1  # ...sharing the one deduped file on disk


def test_guest_render_populates_global_cache_for_later_authed(client, db, counting_source):
    """The cache is content-addressed on disk, not tied to a persisted Track — so even a guest's
    render spares the next identical one (authed or guest) from re-billing TTS."""
    guest_token = client.post("/auth/guest").json()["guest_token"]
    r1 = client.post(
        "/tts",
        json={"text": "rest now, you are safe", "persona_id": "aria"},
        headers={"X-Guest-Token": guest_token},
    )
    assert r1.status_code == 200

    token = _auth_token(client)
    r2 = _tts(client, token)  # identical text + persona + (stub) source
    assert r2.status_code == 200
    assert r2.content == r1.content
    assert counting_source["n"] == 1  # served from the guest-populated global cache
    assert db.scalar(select(Track)) is not None  # ...and the authed user still gets a saved track


def test_guest_credit_released_when_audio_store_fails(client, db, counting_source, monkeypatch):
    """A render that can't be stored must release the guest's reserved generation — a request that
    returns no audio must never burn the one free credit."""
    from lull_api import main as main_mod
    from lull_api.models import GuestCredit
    from lull_api.security import decode_guest_token

    def _boom(*a, **k):
        raise OSError("disk full")

    monkeypatch.setattr(main_mod, "store_audio", _boom)

    guest_token = client.post("/auth/guest").json()["guest_token"]
    r = client.post(
        "/tts",
        json={"text": "rest now, you are safe", "persona_id": "aria"},
        headers={"X-Guest-Token": guest_token},
    )
    assert r.status_code == 503
    credit = db.scalar(
        select(GuestCredit).where(GuestCredit.guest_id == decode_guest_token(guest_token))
    )
    assert credit is not None and credit.used == 0  # reservation released, free credit intact


def test_different_voice_is_not_cache_served(client, db, counting_source):
    token = _auth_token(client)
    _tts(client, token, persona="aria")
    _tts(client, token, persona="james")  # same text, different voice => different audio
    assert counting_source["n"] == 2
