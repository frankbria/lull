# Issue #51 — Audio cache eviction/quota (P[1.1.8a])

**Plan source:** self-authored (no plan comment). Label: `area:api`. Follow-up to #15.

## Problem
`audio_store/` (the content-addressed TTS dedup cache) grows unbounded — no TTL,
LRU, or size quota. A guest can mint fresh tokens + submit unique scripts, so write
volume can grow despite edge rate-limiting.

## Chosen approach — on-write LRU eviction to a configurable byte quota
- `LULL_AUDIO_STORE_MAX_BYTES` (default 1 GiB; `<=0` disables). Bounds disk by design.
- `evict_audio_store(store_dir, max_bytes)` in persistence.py: if total size > cap,
  delete files oldest-mtime-first until under cap. Race-tolerant (file may vanish).
- Called at the end of `store_audio` (on-write check — no background task, ponytail).
- Cache **hit** touches the file's mtime (`os.utime`) so eviction is true LRU
  (least-recently-*used*), not just oldest-written — aligns with the issue's mtime keying.
- No separate TTL sweep: a size quota already bounds disk; TTL is a redundant 2nd knob (YAGNI).

## Why eviction is safe today
No endpoint serves audio from `AudioFile.path` — bytes are returned inline + device-cached
(US-008). So an evicted file just means the next identical render re-synthesizes (correct
cache behavior). **Known limitation:** once a playback-from-store endpoint lands, eviction
must exclude account-scoped files (or re-render on miss) — exactly the issue's own
"only persist cache files for authed generations" follow-up note.

## Steps (TDD)
1. RED: `tests/test_cache_eviction.py` — evict removes oldest until under quota; keeps newest;
   `max_bytes<=0` disables; `store_audio` triggers eviction when over cap.
2. config.py: `audio_store_max_bytes: int = 1024**3`.
3. persistence.py: `evict_audio_store(...)`; call from `store_audio` (new `max_bytes` arg).
4. main.py: pass `settings.audio_store_max_bytes` to `store_audio`; `os.utime` on cache hit.
5. Docs: `.env.example` + update the `store_audio` ponytail comment (the unbounded note is now resolved).
6. GREEN: full suite + ruff/black.

## Acceptance (from issue)
- [ ] TTL/LRU eviction sweep for `audio_store/` (mtime-keyed). → on-write LRU.
- [ ] Configurable max store size (`LULL_AUDIO_STORE_MAX_BYTES`).
- [ ] Edge rate-limiting note (reverse proxy) — deploy verification, documented (not code).
