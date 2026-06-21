import uuid

import httpx
import pytest
from fastapi.testclient import TestClient

from lull_api.audio import ElevenLabsAudioSource
from lull_api.main import app, get_source

# Module client for tests that never reach the generation gate (char-cap, missing-key).
client = TestClient(app)


def teardown_function():
    app.dependency_overrides.clear()


def _source_with(handler) -> ElevenLabsAudioSource:
    return ElevenLabsAudioSource(
        api_key="test-key", voice_id="voiceXYZ", transport=httpx.MockTransport(handler)
    )


def _override(source) -> None:
    app.dependency_overrides[get_source] = lambda: source


def _guest() -> dict[str, str]:
    """A fresh guest id claims its one free generation; the transactional client rolls it back."""
    return {"X-Guest-Id": str(uuid.uuid4())}


def test_tts_success_sends_correct_request_and_returns_audio(client):
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        seen["key"] = request.headers.get("xi-api-key")
        seen["body"] = request.content.decode()
        return httpx.Response(200, content=b"FAKEMP3", headers={"content-type": "audio/mpeg"})

    _override(_source_with(handler))
    r = client.post("/tts", json={"text": "breathe and relax"}, headers=_guest())
    assert r.status_code == 200
    assert r.content == b"FAKEMP3"
    assert r.headers["content-type"] == "audio/mpeg"
    assert seen["url"].endswith("/voiceXYZ")  # voice id routed into the URL
    assert seen["key"] == "test-key"  # auth header sent
    assert "breathe and relax" in seen["body"]  # script text in the request body


@pytest.mark.parametrize(
    "code,exp_status,retryable",
    [(401, 502, False), (429, 502, True), (500, 502, True)],
)
def test_tts_maps_upstream_errors(client, code, exp_status, retryable):
    _override(_source_with(lambda req: httpx.Response(code, text="nope")))
    r = client.post("/tts", json={"text": "hi"}, headers=_guest())
    assert r.status_code == exp_status
    assert r.json()["detail"]["retryable"] is retryable
    assert r.json()["detail"]["message"]  # non-empty, human-readable


def test_tts_maps_timeout_to_retryable(client):
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("timed out", request=request)

    _override(_source_with(handler))
    r = client.post("/tts", json={"text": "hi"}, headers=_guest())
    assert r.status_code == 504
    assert r.json()["detail"]["retryable"] is True


def test_char_cap_rejected_before_any_outbound_call():
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        return httpx.Response(200, content=b"X")

    _override(_source_with(handler))
    r = client.post("/tts", json={"text": "a" * 60001})
    assert r.status_code == 422
    assert calls["n"] == 0  # never reached the network


def test_missing_key_returns_clear_503(monkeypatch):
    from lull_api import main

    monkeypatch.setattr(main.settings, "audio_source", "elevenlabs")
    monkeypatch.setattr(main.settings, "elevenlabs_api_key", None)
    app.dependency_overrides.clear()  # exercise the real get_source dependency
    r = client.post("/tts", json={"text": "hi"})
    assert r.status_code == 503
    assert r.json()["detail"]["retryable"] is False
