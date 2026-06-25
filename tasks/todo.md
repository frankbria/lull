# Issue #14 — Real LLM script generation + hardened prompt + moderation pass

P[1.1.7] · labels: sprint:1, area:api, safety · self-authored plan (no plan comment on issue)

## Acceptance criteria (from issue body, maps to PRD FR-G4/FR-G5)
1. Versioned, injection-resistant system prompt: no dosages, no diagnosis, no therapeutic-outcome promises.
2. Post-generation moderation pass **before TTS** blocks prohibited content (self-harm, named meds beyond user input, age-inappropriate, delusion-reinforcing).
3. PII stripped from LLM/TTS calls.
4. Red-team set of ≥50 scripts: zero harmful bypasses.

## How it fits the codebase (from exploration)
- `scripts.py` is today a deterministic template assembler (`build_script`) — the Sprint-0 stub the issue names.
- `audio.py` already establishes the seam pattern: a `Protocol` + a `Stub*` (offline, no API key) + a real httpx impl with an **injected transport** for boundary tests, errors mapped to HTTP via a typed exception. Mirror it for the LLM call — no new dependency (httpx already in), tests stay offline.
- `/script` endpoint (`main.py`) is the generation step; `/tts` is the render step. PRD pipeline: client → LLM → **moderation** → ElevenLabs. So moderation gates at `/script`.
- Config is `LULL_`-prefixed pydantic-settings.

## Plan (TDD, smallest diff that satisfies the ACs)

### 1. `config.py` — three settings
- `script_source: str = "stub"` (`stub` | `claude`), mirrors `audio_source`.
- `anthropic_api_key: str | None = None`.
- `anthropic_model: str = "claude-opus-4-8"` (Claude-API skill default; overridable via `LULL_ANTHROPIC_MODEL` — sonnet-4-6 is the cheaper pick for this per-generation call if you prefer).

### 2. `scripts.py` — split resolution from generation; add the hardened prompt
- Add `theme: str = ""` to `TrackSpec` — the untrusted "suggestion-theme" free-text FR-G4 names. **Load-bearing**: with no untrusted input, "injection-resistant"/"PII stripped"/"red-team" are vacuous. API-level only; mobile UI wiring is a follow-up.
- `PROMPT_VERSION = "g4-v1"` + `SYSTEM_PROMPT`: hardened — forbids dosages/diagnosis/outcome-promises, instructs that the delimited theme is *content, never instructions*.
- `resolve_components(spec)` — deterministic `ai`-pick resolution (keeps FR-B3 reveal working for both sources).
- `build_user_prompt(spec, resolved)` — wraps the **PII-stripped** theme in explicit delimiters.
- `ScriptSource` Protocol + `StubScriptSource` (current template assembly — existing tests stay green offline) + `ClaudeScriptSource` (httpx → Anthropic Messages API, injected transport, `ScriptSourceError` mapped like `AudioSourceError`). `build_script_source(settings)` factory.

### 3. `pii.py` — `strip_pii(text)` (regex: emails, phone numbers, SSN-like). ponytail: regex now, NER later.

### 4. `moderation.py` — `moderate(script, *, user_input="")` raises `ScriptModerationError(category)`
- Rules/keyword classifier: self-harm, dosages, diagnosis, therapeutic-outcome promises, named-meds-beyond-user-input, age-inappropriate, delusion-reinforcing. ponytail: rules now; LLM classifier is the upgrade path (PRD open question).

### 5. `main.py` — wire it in
- `get_script_source()` dependency (overridable in tests).
- `/script` → `async`: `resolve → generate → moderate(user_input=theme) → estimate/return`. Moderation block → 422 safe message. `ScriptSourceError` → 502/503.

### 6. Tests (`tests/test_safety.py`) — RED first
- `strip_pii` removes emails/phones/SSNs.
- `SYSTEM_PROMPT` carries the version + the three FR-G4 prohibitions; `build_user_prompt` delimits the theme and strips PII from it.
- **Red-team corpus ≥50** harmful scripts across every category → `moderate()` raises for *all* (zero bypass = AC4).
- Benign template outputs pass moderation (no false-positive).
- `/script` with an injected harmful source → 422 (moderation gates before TTS).
- Existing `test_generate.py` stays green (stub default, async endpoint).

## Out of scope (Known Limitations for PR)
- Mobile UI for the theme field (API accepts it; UI wiring later).
- `/tts` direct-call moderation — moderation gates at `/script` per the PRD pipeline; `/tts` keeps the char cap. Follow-up.
- LLM-based moderation/classifier — rules-based now.

## Verify
- [ ] `cd apps/api && uv run pytest` green; ruff + black clean
- [ ] Demo each AC (Phase 11)
