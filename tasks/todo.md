# Issue #2 — P[0.1.2] Wire and verify real ElevenLabs TTS round-trip

**Plan source:** self-authored. **Branch:** `feat/2-elevenlabs-roundtrip`

## Adapted plan
1. Harden `apps/api/src/lull_api/audio.py` `ElevenLabsAudioSource`:
   - Add an optional `transport` seam so the external boundary is testable without a live key.
   - Map failures to a typed `AudioSourceError(message, status_code, retryable)`:
     timeout → retryable; 401 → not retryable ("check API key"); 429 → retryable; 5xx → retryable.
2. `apps/api/src/lull_api/main.py` `/tts`: catch `AudioSourceError` → clear HTTP status
   (502/503/504) + `{detail, retryable}`; missing-key `RuntimeError` → 503. Keep char cap before the call.
3. TDD: `tests/test_elevenlabs.py` via `httpx.MockTransport` — success returns bytes + correct request
   shape (xi-api-key header, voice id in URL, text in body); 401/429/5xx/timeout → mapped status +
   retryable flag; char cap rejected before any outbound call.

## Acceptance criteria
- [ ] `LULL_AUDIO_SOURCE=elevenlabs` + key renders a real script to audio — **needs key (Phase 4)**
- [ ] Audio plays end-to-end on device — **device-only (→ #24-style follow-up)**
- [ ] Hard char cap + cost/time estimate enforced before the charge — **verifiable here**
- [ ] API errors/timeouts return a clear, retryable error — **verifiable here**
