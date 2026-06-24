import asyncio

import httpx
from fastapi.testclient import TestClient

from lull_api import main
from lull_api.audio import ElevenLabsAudioSource, StubAudioSource
from lull_api.main import app, get_source_factory
from lull_api.personas import PERSONA_VOICE_IDS, resolve_voice_id

# Preview is ungated, so a module client (no DB) suffices for it.
client = TestClient(app)


def teardown_function():
    app.dependency_overrides.clear()
    main._preview_cache.clear()  # previews are cached per persona; don't leak across tests


def _factory(handler):
    """Override the source factory with one that HONORS the requested voice id, so the mock handler
    sees the persona's real voice id in the outbound URL."""

    def make(voice_id=None):
        return ElevenLabsAudioSource(
            "test-key", voice_id or "default", transport=httpx.MockTransport(handler)
        )

    app.dependency_overrides[get_source_factory] = lambda: make


def _guest(c) -> dict[str, str]:
    return {"X-Guest-Token": c.post("/auth/guest").json()["guest_token"]}


def test_at_least_six_personas_with_distinct_voice_ids():
    # AC1: >=6 personas, each abstracted to a real (non-empty), distinct voice id.
    assert len(PERSONA_VOICE_IDS) >= 6
    ids = list(PERSONA_VOICE_IDS.values())
    assert all(ids) and len(set(ids)) == len(ids)


def test_resolve_unknown_persona_is_none():
    assert resolve_voice_id("nope") is None


def test_preview_returns_audio_in_persona_voice_ungated():
    # AC2: a preview clip per persona — no guest token, and the persona's voice id routed upstream.
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        return httpx.Response(200, content=b"PREVIEWMP3", headers={"content-type": "audio/mpeg"})

    _factory(handler)
    r = client.get("/voices/sarah/preview")  # no auth/guest header
    assert r.status_code == 200
    assert r.content == b"PREVIEWMP3"
    assert seen["url"].endswith("/" + PERSONA_VOICE_IDS["sarah"])  # right voice, abstracted from id


def test_preview_is_cached_after_first_synthesis():
    # The ungated endpoint must not amplify into repeated billable synths — second hit is cached.
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        return httpx.Response(200, content=b"MP3", headers={"content-type": "audio/mpeg"})

    _factory(handler)
    assert client.get("/voices/aria/preview").status_code == 200
    assert client.get("/voices/aria/preview").status_code == 200
    assert calls["n"] == 1  # one upstream synthesis, then served from cache


def test_preview_single_flight_under_concurrent_cold_requests():
    # The cost cap must hold under load: many concurrent cold requests for one persona share a single
    # synthesis rather than each firing their own.
    calls = {"n": 0}

    class Slow(StubAudioSource):
        async def synthesize(self, text: str) -> bytes:
            calls["n"] += 1
            await asyncio.sleep(0.05)  # widen the window so requests genuinely overlap
            return await super().synthesize(text)

    app.dependency_overrides[get_source_factory] = lambda: (lambda v=None: Slow())

    async def hammer():
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://t") as ac:
            return await asyncio.gather(*[ac.get("/voices/aria/preview") for _ in range(5)])

    results = asyncio.run(hammer())
    assert all(r.status_code == 200 for r in results)
    assert calls["n"] == 1  # five concurrent cold hits -> one synthesis


def test_preview_unknown_persona_is_404():
    _factory(lambda req: httpx.Response(200, content=b"X"))
    r = client.get("/voices/bogus/preview")
    assert r.status_code == 404


def test_tts_routes_selected_persona_voice(client):
    # AC3 plumbing: the saved persona flows into the render as its voice id.
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        return httpx.Response(200, content=b"MP3", headers={"content-type": "audio/mpeg"})

    _factory(handler)
    r = client.post("/tts", json={"text": "relax", "persona_id": "james"}, headers=_guest(client))
    assert r.status_code == 200
    assert seen["url"].endswith("/" + PERSONA_VOICE_IDS["james"])


def test_tts_unknown_persona_rejected_before_network(client):
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        return httpx.Response(200, content=b"X")

    _factory(handler)
    r = client.post("/tts", json={"text": "hi", "persona_id": "bogus"}, headers=_guest(client))
    assert r.status_code == 422
    assert calls["n"] == 0  # never reached the network
