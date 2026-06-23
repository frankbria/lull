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
  mobile/     Expo / React Native app — track builder (component selection) + Sprint-0 test harness
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

## CI
GitHub Actions runs on every PR (`.github/workflows/`):
- **`ci.yml`** — api (`ruff` + `pytest` against a Postgres service) and mobile (`tsc` + `eslint`).
- **`codex-review.yml`** — an automated, advisory cross-family code review via OpenAI Codex,
  independent of CodeRabbit. Posts findings as a sticky PR comment; never blocks merge. Requires
  an `OPENAI_API_KEY` repo secret (`gh secret set OPENAI_API_KEY`); skips cleanly when unset or on forks.

## Device delivery (EAS Build + OTA)
Internal dev-test loop: install once, then every merge to `main` pushes an over-the-air JS/asset
update that the app pulls **automatically on next cold start** (`expo-updates` `checkAutomatically:
ON_LOAD`). This is *not* store distribution (Sprint 6).

**One-time setup**
1. `EXPO_TOKEN` repo secret (create at expo.dev → Access Tokens): `gh secret set EXPO_TOKEN`.
   The OTA workflow no-ops until this is set.
2. Build + install the internal APK on the Android device (Expo's infra builds it):
   ```bash
   cd apps/mobile
   eas build --profile preview --platform android   # subscribes the build to the `preview` channel
   ```
   Install the resulting APK on the device (open the build link, or `eas build:run`).
3. **API base for the standalone build.** A built APK has no Metro host to derive the API URL from,
   so it falls back to `localhost:8000` (the phone itself). Set the repo **variable**
   `EXPO_PUBLIC_API_BASE` to a device-reachable API URL (`gh variable set EXPO_PUBLIC_API_BASE`); the
   OTA workflow embeds it into each published bundle. **Use HTTPS:** a release-mode APK blocks
   cleartext (plain `http://`) traffic on modern Android, so a plain-HTTP dev API (e.g. an
   `http://100.x.y.z:8000` Tailscale box) won't be reachable from the build. Front the dev API with
   TLS, or — for dev only, never production — enable cleartext via the `expo-build-properties`
   plugin (`android.usesCleartextTraffic: true`). API connectivity for on-device builds is tracked
   with the device-proving work (#24), separate from these delivery rails.

**How updates flow**
- Merge to `main` → `.github/workflows/eas-update.yml` runs `eas update --channel preview` → the
  installed build **downloads** the new bundle on its next launch and **applies it on the following
  cold start** (`checkAutomatically: ON_LOAD` + `fallbackToCacheTimeout: 0` — the app starts
  instantly from cache and swaps in the update on the next relaunch, rather than blocking startup on
  the network).
- **Foreground-resume caveat:** the check happens on app **launch/cold start**, not on resume from
  background. A long-backgrounded app applies the update the next time it's fully relaunched.

**Native-change caveat (important)**
OTA only ships JS/assets over the *existing* native runtime. `runtimeVersion` uses the
**`fingerprint`** policy: adding a native module/permission (or other native change) automatically
changes the computed runtimeVersion, so the OTA targets a *new* runtime that your already-installed
build doesn't subscribe to — it simply won't pull an incompatible bundle (no crash, no manual
`version` bump needed). To pick up a native change on the device you must do a fresh
`eas build --profile preview` + install; pure JS/asset changes flow over OTA automatically.

## Docs
- [`docs/PRD.md`](docs/PRD.md) — product requirements
- [`docs/ROADMAP.md`](docs/ROADMAP.md) — sprints + risk gates
- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — stack, pipeline, data model
- [`docs/NAMING.md`](docs/NAMING.md) — naming & domain research (name deferred)
