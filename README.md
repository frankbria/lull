# Lull *(working codename — not final)*

Wellness app that generates personalized self-hypnosis / meditation audio tracks from
user-chosen components (AI script + ElevenLabs voice), built for long, uninterrupted,
customizable sessions — including ketamine-assisted therapy (KAP) and psychedelic-assisted
contexts that mainstream apps refuse to support.

> **Positioning:** wellness / self-help. No medical claims. Not a substitute for clinical care.

## Status
Discovery complete. See [`docs/PRD.md`](docs/PRD.md) for the full product requirements.

- **MVP:** Track Builder + Player (Sprints 0–2)
- **Stack:** Expo / React Native (TS) · FastAPI · PostgreSQL (SQLAlchemy + Alembic) · Python-native auth
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
**Database** (Postgres via Docker — also creates the `lull_test` / `lull_migtest` databases tests use):
```bash
docker compose -f apps/api/docker-compose.yml up -d        # local Postgres on :5432
cd apps/api && uv run alembic upgrade head                 # apply migrations to the dev DB
```
Staging/prod: set `LULL_DATABASE_URL` to the managed/VPS Postgres DSN (overrides the local default).

**API** (no key needed — runs on the stub AudioSource):
```bash
cd apps/api && uv sync
uv run pytest -q                                   # 20 passing (needs the Postgres above)
uv run uvicorn lull_api.main:app --reload          # http://localhost:8000  (/health, /script, /tts)
```
Real ElevenLabs round-trip: copy `apps/api/.env.example` → `.env`, set `LULL_AUDIO_SOURCE=elevenlabs`
and `LULL_ELEVENLABS_API_KEY`.

**Mobile** (Expo SDK 54; deps reconciled via the workspace install):
```bash
pnpm install                           # from repo root — installs the workspace
cd apps/mobile
pnpm exec expo start                    # --android / --ios / --web
```
The app **auto-derives the API base** from the Metro host it connects to (same host, port
8000) — no per-target config for the common case. Overrides:
- **Physical device over LAN/Tailscale:** start Metro advertising a phone-reachable host so the
  derived API base matches —
  `REACT_NATIVE_PACKAGER_HOSTNAME=<reachable-ip> pnpm exec expo start`
  (Expo Go must match the project's SDK; the API must bind `--host 0.0.0.0`).
- **Anything non-default** (staging, a separate API box): set `EXPO_PUBLIC_API_BASE` explicitly
  (e.g. `http://10.0.2.2:8000` for the Android emulator) — it always wins over derivation.

## Docs
- [`docs/PRD.md`](docs/PRD.md) — product requirements
- [`docs/ROADMAP.md`](docs/ROADMAP.md) — sprints + risk gates
- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — stack, pipeline, data model
- [`docs/NAMING.md`](docs/NAMING.md) — naming & domain research (name deferred)
