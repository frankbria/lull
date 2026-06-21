from fastapi.testclient import TestClient

from lull_api.audio import StubAudioSource
from lull_api.main import app, get_source

client = TestClient(app)


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_script_resolves_ai_choices_and_estimates():
    r = client.post("/script", json={"hypnosis": True})
    assert r.status_code == 200
    body = r.json()
    assert body["char_count"] > 0
    assert body["est_seconds"] > 0
    # 'ai' picks must be revealed as concrete component choices (FR-B3)
    assert set(body["components"]) == {"induction", "deepener", "body", "ending"}
    assert "ai" not in body["components"].values()


def test_script_rejects_unknown_component():
    r = client.post("/script", json={"induction": "nope"})
    assert r.status_code == 422


def test_tts_stub_returns_playable_wav(client):
    """client fixture = transactional DB; a guest id claims the one free generation."""
    import uuid

    app.dependency_overrides[get_source] = lambda: StubAudioSource()
    try:
        r = client.post(
            "/tts",
            json={"text": "rest now, you are safe"},
            headers={"X-Guest-Id": str(uuid.uuid4())},
        )
        assert r.status_code == 200
        assert r.headers["content-type"] == "audio/wav"
        assert r.content[:4] == b"RIFF"  # valid WAV header
    finally:
        app.dependency_overrides.pop(get_source, None)


def test_meditation_vs_hypnosis_opener_differs():
    hyp = client.post("/script", json={"hypnosis": True}).json()["script"]
    med = client.post("/script", json={"hypnosis": False}).json()["script"]
    assert hyp != med
