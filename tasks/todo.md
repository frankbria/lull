# US-005 Voice persona selection + preview (issue #12)

## Acceptance criteria
1. ≥6 personas (name + descriptor), abstracted from raw ElevenLabs IDs
2. 20–30s preview per persona in hypnosis cadence (slow, warm)
3. Selection saved; changing voice after generation triggers re-render

**Out of scope:** FR-V3 warmth/pace controls (not in this issue's AC — YAGNI).

## Design (mirror existing patterns: HypnosisToggle persistence, CategorySection radio, AudioSource seam)

Persona abstraction split, matching how the component catalog is already duplicated
(mobile `catalog.ts` ↔ api `scripts.py`): public {id,name,descriptor} on the client,
the secret id→ElevenLabs-voice-id map stays server-only. No raw voice IDs reach the client.

### Shared (`packages/shared/src/index.ts`)
- [ ] Add `VoicePersona {id,name,descriptor}`, `VOICE_PERSONAS` (6 calm/warm personas), `DEFAULT_VOICE_ID`.

### Backend (`apps/api`)
- [ ] `personas.py`: `PERSONA_VOICE_IDS: dict[id, elevenlabs_voice_id]` (6, real premade IDs) + `resolve_voice_id(persona_id) -> str | None`. Canned ~25s slow/warm `PREVIEW_TEXT`.
- [ ] `audio.py`: `get_audio_source(settings, voice_id=None)` — optional per-call voice override.
- [ ] `main.py`:
  - `TtsIn.persona_id: str | None = None`; `/tts` resolves persona→voice_id (unknown → 422), builds source with override. Backward compatible (None → config default).
  - `GET /voices/{persona_id}/preview` — **ungated** (preview must not burn the free generation); unknown → 404; synth `PREVIEW_TEXT` with persona voice → audio bytes.
- [ ] Tests `tests/test_voices.py`: preview 200 (valid, no guest token needed) / 404 (invalid); persona routed into ElevenLabs URL; `/tts` persona_id routes correct voice; unknown persona_id → 422.

### Mobile (`apps/mobile`)
- [ ] `preferences.ts`: add `VOICE_KEY`, `loadVoice`/`saveVoice` (mirror hypnosis).
- [ ] `TrackBuilderContext`: `voiceId` (default `DEFAULT_VOICE_ID`) + `setVoiceId`, persisted on change, loaded on mount.
- [ ] `audio.ts`: `synthesizeAndPlay(text, personaId?)` adds `persona_id` to `/tts`; new `playVoicePreview(personaId)` GETs the preview clip, plays, returns cleanup.
- [ ] `VoicePicker.tsx`: radio list over `VOICE_PERSONAS` (mirror HypnosisToggle), per-row "Preview" button → `playVoicePreview`.
- [ ] `TrackBuilderScreen`: render `<VoicePicker/>`; thread `voiceId` into `proceedToAudio`; release current audio when `voiceId` changes (AC3 re-render — no persisted track yet, so re-render = drop stale audio → next play uses new voice).
- [ ] Tests `voicePicker.test.tsx`: renders ≥6 personas, default selected, selection persists, preview triggers playback; persona threaded into `/tts`; voice change releases prior audio.

## Verify
- [ ] `cd apps/api && uv run pytest -q` + `cd apps/mobile && pnpm exec jest` green
- [ ] Demo each AC (Phase 11)
