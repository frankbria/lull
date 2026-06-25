# P[1.1.8] US-008 — Persist generated track + local cache (issue #15)

**Plan source:** self-authored (issue had no plan comment). Label: `area:api`.

## Acceptance criteria
- [x] AC1: Generated track saved to backend (account-scoped) + local device cache
- [x] AC2: Metadata stored: components, voice, duration, hypnosis flag, date
- [x] AC3: Identical scripts hashed + cache-served to avoid duplicate TTS spend

**Done.** Demo (live, real Postgres + disk) showed: authed /tts persists Track +
4 components (ai_chosen correct) + AudioFile (duration/source/checksum/date),
identical render by a 2nd user served from cache (0 extra synth, 1 shared file,
2 tracks), different voice re-synthesized. Cache is content-addressed on disk +
global (guest renders spare later ones). Device cache: mobile audio.ts replays
by content hash, skipping /tts (jest-verified).

## Key finding
The data model already exists and was built ahead for exactly this: `Track`
(spec JSONB, status, created_at, user_id), `TrackComponent` (category, choice,
ai_chosen), `AudioFile` (path, **checksum index**, duration_seconds, source).
**No DB migration needed** — only endpoint logic.

## Design decisions / assumptions
- **Account-scoped persistence = authed users only.** `Track.user_id` is a NOT
  NULL FK; guests have no user row, so a guest generation produces audio (and
  benefits from the dedup cache) but no saved Track. Auth UI is a separate
  story; the real client currently always uses a guest token, so persistence is
  exercised via authed API/tests until the auth UI lands. (Known limitation.)
- **Dedup cache is global** (by checksum over text+voice) so it saves TTS spend
  for everyone; only the Track *record* is account-scoped.
- **Voice** stored inside `Track.spec` JSONB (`persona_id` key) — no new column.
- **Duration** = `len(text)/12.5` (same ~150 wpm heuristic as `/script`
  est_seconds); real container parsing is out of scope (ponytail).
- **Local device cache**: key the on-device audio file by a content hash of
  (text + persona); replay from cache and skip `/tts` on an identical re-render.

## Steps (TDD: tests first)
1. **config**: add `audio_store_dir: str = "audio_store"` to `config.py`.
2. **persistence.py** (new): `script_checksum(text, voice_id)`,
   `find_cached_audio(db, checksum)`, `store_audio(bytes, checksum, ext, dir)`
   (write `{checksum}.{ext}`, idempotent), `persist_track(db, user_id, spec,
   components, persona_id, path, checksum, duration, source)`.
3. **main.py `/tts`**: compute checksum → cache-lookup before synth (serve
   cached bytes on hit, skip TTS) → on miss synthesize + store file → if authed
   and `spec` provided, persist Track + components + AudioFile. Response bytes
   unchanged (client-compatible).
4. **TtsIn**: add optional `spec: TrackSpecIn | None` + `components: dict|None`
   so a full track can be persisted (ai_chosen derived from spec[cat]=="ai").
5. **mobile audio.ts**: content-hash cache key; reuse cached file / skip `/tts`
   on identical re-render. Web: in-memory hash→blobURL map.

## Tests
- API: persist-on-authed, dedup-skips-synth (count synth calls), global cache
  hit (guest then authed), guest-creates-no-track, existing tests still green,
  alembic migration test unchanged (no schema change).
- Mobile: cache key helper + short-circuit (mocked fetch) skips second /tts.

## Verify
- [ ] `cd apps/api && uv run pytest` green; ruff + black clean
- [ ] mobile `pnpm test` green
- [ ] Demo each AC (Phase 11)
