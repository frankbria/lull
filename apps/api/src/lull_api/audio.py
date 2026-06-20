"""AudioSource seam — the key abstraction (see docs/ARCHITECTURE.md).

All audio flows through `AudioSource.synthesize`, so swapping ElevenLabs-cached for real-time
streaming, owned music beds, etc. is a new implementation, not a rewrite. MVP ships two:
- StubAudioSource: valid silent WAV, lets the whole app run/test offline with no API key.
- ElevenLabsAudioSource: real TTS.
"""

from __future__ import annotations

import struct
from typing import Protocol

import httpx

from .config import Settings


class AudioSourceError(Exception):
    """A synthesis failure with a clear, client-facing message and retry guidance."""

    def __init__(self, message: str, *, status_code: int, retryable: bool) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code  # HTTP status the API should return
        self.retryable = retryable


class AudioSource(Protocol):
    media_type: str

    async def synthesize(self, text: str) -> bytes: ...


def _silence_wav(seconds: float, sample_rate: int = 16_000) -> bytes:
    """Minimal valid mono 16-bit PCM WAV of silence — a real, playable file for the harness."""
    n_samples = int(seconds * sample_rate)
    data_size = n_samples * 2  # 16-bit
    header = b"RIFF" + struct.pack("<I", 36 + data_size) + b"WAVE"
    header += b"fmt " + struct.pack("<IHHIIHH", 16, 1, 1, sample_rate, sample_rate * 2, 2, 16)
    header += b"data" + struct.pack("<I", data_size)
    return header + b"\x00" * data_size


class StubAudioSource:
    media_type = "audio/wav"

    async def synthesize(self, text: str) -> bytes:
        # ~150 wpm hypnosis pacing ≈ 12.5 chars/sec; cap the stub so tests stay fast.
        seconds = min(max(len(text) / 12.5, 1.0), 30.0)
        return _silence_wav(seconds)


class ElevenLabsAudioSource:
    media_type = "audio/mpeg"

    def __init__(
        self,
        api_key: str,
        voice_id: str,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._api_key = api_key
        self._voice_id = voice_id
        self._transport = transport  # injected in tests to drive the external boundary

    async def synthesize(self, text: str) -> bytes:
        url = f"https://api.elevenlabs.io/v1/text-to-speech/{self._voice_id}"
        try:
            async with httpx.AsyncClient(timeout=300, transport=self._transport) as client:
                resp = await client.post(
                    url,
                    headers={"xi-api-key": self._api_key, "accept": "audio/mpeg"},
                    json={"text": text, "model_id": "eleven_multilingual_v2"},
                )
                resp.raise_for_status()
                return resp.content
        except httpx.TimeoutException as exc:
            raise AudioSourceError(
                "Voice service timed out — please try again.",
                status_code=504,
                retryable=True,
            ) from exc
        except httpx.HTTPStatusError as exc:
            raise _map_status_error(exc.response.status_code) from exc
        except httpx.RequestError as exc:
            raise AudioSourceError(
                "Could not reach the voice service — please try again.",
                status_code=502,
                retryable=True,
            ) from exc


def _map_status_error(code: int) -> AudioSourceError:
    if code in (401, 403):
        return AudioSourceError(
            "Voice service rejected the API key.", status_code=502, retryable=False
        )
    if code == 429:
        return AudioSourceError(
            "Voice service is rate limited — please retry shortly.",
            status_code=502,
            retryable=True,
        )
    if code >= 500:
        return AudioSourceError(
            "Voice service is temporarily unavailable — please try again.",
            status_code=502,
            retryable=True,
        )
    return AudioSourceError(
        f"Voice service returned an unexpected error ({code}).",
        status_code=502,
        retryable=False,
    )


def get_audio_source(settings: Settings) -> AudioSource:
    if settings.audio_source == "elevenlabs":
        if not settings.elevenlabs_api_key:
            raise RuntimeError("LULL_AUDIO_SOURCE=elevenlabs but LULL_ELEVENLABS_API_KEY is unset")
        return ElevenLabsAudioSource(settings.elevenlabs_api_key, settings.elevenlabs_voice_id)
    return StubAudioSource()
