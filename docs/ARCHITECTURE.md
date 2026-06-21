# Architecture

High-level shape for the MVP. Detail and rationale in [`PRD.md`](PRD.md) §9.

## Stack
- **Client:** Expo / React Native (TypeScript, strict). Android **foreground media service +
  MediaSession** for long background playback (built in Sprint 2, not retrofitted). Local audio
  cache + on-disk playback-position store.
- **Backend:** FastAPI (Python, `uv`), **PostgreSQL** (SQLAlchemy 2.0 + Alembic migrations).
  **Auth is Python-native** — Authlib (OAuth), passlib/argon2 (password hashing), JWT/session
  tokens — kept in-process so the backend stays one language and one deploy unit. *(BetterAuth was
  the original pick but is Node/TS-only; running it would mean a second runtime + cross-service
  session verification, not worth it for a solo MVP on a shared VPS.)*
- **Monorepo:** `apps/mobile` (Expo) · `apps/api` (FastAPI) · `packages/shared` (TS types shared
  across client/contract).

## Generation pipeline
```
client → POST /generate → LLM (script) → moderation pass → ElevenLabs (voice) → cached audio file
                                                                                 (device + cloud)
```
- Script is returned to the client for **preview before TTS** (cost + safety gate).
- Hard character cap + cost/time estimate before the ElevenLabs charge.
- Identical scripts are hashed and **cache-served** to avoid duplicate TTS spend.

## `AudioSource` abstraction (the key seam)
A single interface fronts all audio so provider/source swaps are **data, not rewrites**:
- MVP impl: **ElevenLabs cached file**.
- Later impls (no client changes): real-time TTS streaming, **owned music beds** (Frank's
  compositions + ElevenLabs Music), and — low priority — third-party streams.
- Music beds are **tagged data** (mood/context, loop points), not new code paths.

## Data model (initial)
`User` · `Track` (spec + status) · `TrackComponent` (category, choice, ai_chosen flag) ·
`AudioFile` (path, checksum, duration, source) · `SessionLog` (position, partial flag, rating) ·
`MusicBed` (tags, loop points) · `Entitlement` / `GenerationCredit`.

## Cross-cutting requirements
- **Offline-first playback** of fully-downloaded tracks; no mid-session network dependency.
- **PII minimization:** strip name/email/account-id from LLM/TTS calls; no session-content in analytics.
- **Separability:** no PHI in the app backend by default (keeps the telehealth-integration fork open — PRD §5.1).

## Hosting
Hostinger dev VPS for staging — check shared-VPS **port conflicts** and **CORS** (headers + URLs)
before first remote deploy.
