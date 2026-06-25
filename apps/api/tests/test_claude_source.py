"""Boundary tests for ClaudeScriptSource — drive the Anthropic call offline via an injected
transport (same pattern as test_elevenlabs.py). No async test plugin needed: asyncio.run drives the
coroutine, so there's no new dev dependency."""

import asyncio
import json

import httpx
import pytest

from lull_api.scripts import (
    SYSTEM_PROMPT,
    ClaudeScriptSource,
    ScriptSourceError,
    TrackSpec,
    resolve_components,
)


def _source_with(handler) -> ClaudeScriptSource:
    return ClaudeScriptSource(
        api_key="test-key", model="claude-opus-4-8", transport=httpx.MockTransport(handler)
    )


def _generate(source, spec) -> str:
    return asyncio.run(source.generate(spec, resolve_components(spec)))


def test_sends_hardened_prompt_and_returns_text():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["key"] = request.headers.get("x-api-key")
        seen["version"] = request.headers.get("anthropic-version")
        seen["body"] = json.loads(request.content)
        return httpx.Response(
            200,
            json={"stop_reason": "end_turn", "content": [{"type": "text", "text": "Rest now."}]},
        )

    spec = TrackSpec(theme="ocean calm, reach me at a@b.com")
    text = _generate(_source_with(handler), spec)

    assert text == "Rest now."
    assert seen["key"] == "test-key"
    assert seen["version"] == "2023-06-01"
    assert (
        seen["body"]["system"] == SYSTEM_PROMPT
    )  # the versioned, hardened prompt is actually sent
    user_content = seen["body"]["messages"][0]["content"]
    assert "<theme>" in user_content  # theme delimited
    assert "a@b.com" not in user_content  # PII stripped before the call


def test_truncated_completion_is_rejected():
    source = _source_with(
        lambda req: httpx.Response(
            200,
            json={"stop_reason": "max_tokens", "content": [{"type": "text", "text": "Rest no"}]},
        )
    )
    with pytest.raises(ScriptSourceError) as exc:
        _generate(source, TrackSpec())
    assert exc.value.retryable is True


@pytest.mark.parametrize(
    "body",
    [
        "not json at all",
        '{"content": null}',
        '{"content": "oops"}',
        '{"content": ["not-a-block"]}',
        '{"content": [{"type": "text", "text": null}]}',
        '{"content": [{"type": "text", "text": 42}]}',
    ],
)
def test_malformed_response_becomes_safe_error(body):
    source = _source_with(lambda req: httpx.Response(200, text=body))
    with pytest.raises(ScriptSourceError) as exc:
        _generate(source, TrackSpec())
    assert exc.value.status_code == 502


def test_refusal_becomes_safe_422():
    source = _source_with(
        lambda req: httpx.Response(200, json={"stop_reason": "refusal", "content": []})
    )
    with pytest.raises(ScriptSourceError) as exc:
        _generate(source, TrackSpec())
    assert exc.value.status_code == 422
    assert exc.value.retryable is False


@pytest.mark.parametrize("code,retryable", [(401, False), (429, True), (500, True)])
def test_maps_upstream_errors(code, retryable):
    source = _source_with(lambda req: httpx.Response(code, text="nope"))
    with pytest.raises(ScriptSourceError) as exc:
        _generate(source, TrackSpec())
    assert exc.value.retryable is retryable


def test_timeout_is_retryable():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("timed out", request=request)

    with pytest.raises(ScriptSourceError) as exc:
        _generate(_source_with(handler), TrackSpec())
    assert exc.value.status_code == 504
    assert exc.value.retryable is True
