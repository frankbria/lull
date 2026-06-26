"""Cost gate on /script in claude (billable) mode — issue #48.

Stub mode is free and stays ungated. In claude mode each call is a billable Anthropic request, so an
unauthenticated caller must not be able to hammer /script. We cap calls per client IP per window;
an over-limit call gets 429 BEFORE the LLM call fires. A fake source stands in for Anthropic so the
test exercises the gate, not the network.
"""

import pytest
from fastapi.testclient import TestClient

from lull_api.config import settings
from lull_api.main import _script_rate, app, get_script_source

client = TestClient(app)


class _FakeSource:
    """Billable-source stand-in: returns a canned safe script, no network."""

    def __init__(self) -> None:
        self.calls = 0

    async def generate(self, spec, resolved) -> str:
        self.calls += 1
        return "Rest now, you are safe. Let your breath settle and your body soften."


@pytest.fixture
def claude_mode(monkeypatch):
    """Put the app in claude (billable) mode with a fake source and a fresh rate-limit window."""
    src = _FakeSource()
    monkeypatch.setattr(settings, "script_source", "claude")
    app.dependency_overrides[get_script_source] = lambda: src
    _script_rate.clear()
    try:
        yield src
    finally:
        app.dependency_overrides.pop(get_script_source, None)
        _script_rate.clear()


def test_script_rate_limited_in_claude_mode(monkeypatch, claude_mode):
    monkeypatch.setattr(settings, "script_rate_limit_per_min", 2)
    # First N calls from the same IP go through (billable).
    for _ in range(2):
        assert client.post("/script", json={"hypnosis": True}).status_code == 200
    # The next is rejected BEFORE reaching the source.
    r = client.post("/script", json={"hypnosis": True})
    assert r.status_code == 429
    assert "Retry-After" in r.headers
    assert claude_mode.calls == 2  # the rejected call never hit the billable source


def test_limit_zero_disables_gate(monkeypatch, claude_mode):
    monkeypatch.setattr(settings, "script_rate_limit_per_min", 0)  # operator escape hatch
    for _ in range(5):
        assert client.post("/script", json={"hypnosis": True}).status_code == 200


def test_script_not_limited_in_stub_mode(monkeypatch):
    monkeypatch.setattr(settings, "script_source", "stub")
    monkeypatch.setattr(settings, "script_rate_limit_per_min", 2)
    _script_rate.clear()
    # Stub is free → no gate, even well past the claude-mode limit.
    for _ in range(5):
        assert client.post("/script", json={"hypnosis": True}).status_code == 200
