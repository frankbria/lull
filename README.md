# Lull *(working codename — not final)*

Wellness app that generates personalized self-hypnosis / meditation audio tracks from
user-chosen components (AI script + ElevenLabs voice), built for long, uninterrupted,
customizable sessions — including ketamine-assisted therapy (KAP) and psychedelic-assisted
contexts that mainstream apps refuse to support.

> **Positioning:** wellness / self-help. No medical claims. Not a substitute for clinical care.

## Status
Discovery complete. See [`docs/PRD.md`](docs/PRD.md) for the full product requirements.

- **MVP:** Track Builder + Player (Sprints 0–2)
- **Stack:** Expo / React Native (TS) · FastAPI · BetterAuth · PostgreSQL
- **Audio:** pre-generate + cache via a pluggable `AudioSource` layer

## Repo layout
```
apps/
  api/        FastAPI backend — script assembly + ElevenLabs TTS via the AudioSource seam (runnable, tested)
  mobile/     Expo / React Native app — Sprint-0 test harness (init with `npx expo install`)
packages/
  shared/     TypeScript contract types shared by client + API
docs/         PRD, roadmap, architecture, naming research
```

## Develop
**API** (no key needed — runs on the stub AudioSource):
```bash
cd apps/api && uv sync
uv run pytest -q                                   # 5 passing
uv run uvicorn lull_api.main:app --reload          # http://localhost:8000  (/health, /script, /tts)
```
Real ElevenLabs round-trip: copy `apps/api/.env.example` → `.env`, set `LULL_AUDIO_SOURCE=elevenlabs`
and `LULL_ELEVENLABS_API_KEY`.

**Mobile** (initialize once):
```bash
cd apps/mobile && npx expo install     # reconciles Expo SDK 52 deps
npx expo start                         # set EXPO_PUBLIC_API_BASE for device/emulator host
```

## Docs
- [`docs/PRD.md`](docs/PRD.md) — product requirements
- [`docs/ROADMAP.md`](docs/ROADMAP.md) — sprints + risk gates
- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — stack, pipeline, data model
- [`docs/NAMING.md`](docs/NAMING.md) — naming & domain research (name deferred)
