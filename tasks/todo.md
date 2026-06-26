# Issue #48 — Gate /script generation when LLM-backed (cost abuse vector)

**Plan source:** self-authored (issue had no plan comment; only CodeRabbit's planner prompt).
Labels: `sprint:1`, `area:api`, `safety`.

## Problem
In `LULL_SCRIPT_SOURCE=claude` mode, `POST /script` makes a billable Anthropic
call with no auth/quota/rate-limit gate. Unauthenticated callers can hammer it
to drive cost. `/tts` is already gated; `/script` is not. Stub mode is free, so
the vector only exists in a deployed claude-backed env.

## Chosen approach (preserves free-preview UX, no client change)
Per-IP fixed-window **rate limit** on `/script`, active **only in claude (billable) mode**.
- No guest token required → US-006 free-preview flow unchanged (no friction, no client edit).
- Bounds repeated billable calls per IP per window → satisfies "cannot be unbounded".
- Stub mode stays completely ungated → offline dev + existing tests unaffected.
- Rejected calls return 429 + Retry-After; the LLM call never fires when over limit.

Why not "require a guest token": a token doesn't bound per-token call volume
(preview consumes no generation), so it adds client friction without capping cost.
A rate limit is the mechanism that actually bounds cost in-app.

## Steps (TDD)
1. RED: `tests/test_script_rate_limit.py` — claude mode, fake source; Nth+1 call from
   same IP → 429; stub mode → no limit; limiter resets per test.
2. config.py: add `script_rate_limit_per_min: int = 10` (<=0 disables).
3. main.py: small in-process fixed-window limiter (mirrors `_preview_cache` pattern);
   check in `generate_script` before `source.generate`, only when source is billable (claude).
   429 + Retry-After when exceeded.
4. Docs: `.env.example` + config comment for the new setting.
5. GREEN: full test suite + ruff/black.

## Acceptance
- [ ] claude mode: `/script` cannot be used as an unbounded billable endpoint by an unauth caller.
- [ ] Free-preview UX (US-006) preserved (stub unchanged; claude adds only a per-IP ceiling).

## Known ceilings (ponytail)
- In-process limiter: single-instance only; multi-instance needs a shared store (Redis).
- Behind a reverse proxy, `request.client.host` is the proxy IP unless XFF is honored →
  becomes a global cap rather than per-client. Documented; edge per-IP is the deploy concern.
