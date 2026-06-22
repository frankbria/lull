# P[0.1.6a] CI: automated cross-family PR review independent of CodeRabbit — Issue #37

## Acceptance criteria
- [ ] On every PR, CI runs an automated review independent of CodeRabbit; surfaces findings (PR comment).
- [ ] Findings visible on the PR; Critical/Major easy to triage before merge.
- [ ] Resilient to a single reviewer being down (CodeRabbit down -> CI reviewer still posts).
- [ ] Reviewer secrets stored as GitHub Actions secrets, not in the repo.
- [ ] Idempotent; doesn't block on transient outages. Policy = **advisory**.

## Decisions (approved)
- Reviewer: **OpenAI Codex** via `openai/codex-action` (SHA-pinned v1.8 `e0fdf01…`). Non-Claude, non-CodeRabbit.
- Policy: **advisory** — posts a PR comment; NOT a required check; transient outage doesn't block.
- Secret `OPENAI_API_KEY` added by owner **after merge**; workflow no-ops gracefully until then.

## Plan
1. New `.github/workflows/codex-review.yml` (separate from ci.yml — independent + easy to disable):
   - `on: pull_request` [opened, reopened, synchronize, ready_for_review]; skip drafts (cost).
   - `permissions: contents: read, pull-requests: write`; per-PR `concurrency` cancel-in-progress.
   - **guard step**: read `OPENAI_API_KEY` into env; emit `has_key`. Empty (fork / unset) -> skip the
     review + post steps. (This IS the resilience/skip path.)
   - checkout `fetch-depth: 0` (needs base SHA for the diff).
   - `openai/codex-action@<sha>`: `openai-api-key`, review `prompt` (diff vs base.sha; markdown grouped
     Critical/Major first), `sandbox: read-only`, `output-file`. `continue-on-error: true` (advisory).
   - **sticky comment**: marker `<!-- codex-review -->`, find-and-update-or-create via `gh api`
     (idempotent — re-run updates in place, no comment spam).
2. `ci.yml` unchanged; review job is NOT added to required checks (advisory).
3. README: note the CI review step + that it needs `OPENAI_API_KEY`.

## Out of scope (YAGNI)
- Inline per-line comments + JSON-schema parsing (cookbook's heavier path) — sticky markdown summary
  is enough for advisory triage; revisit if we make it blocking.
- Label/size cost-gating — cancel-superseded + draft-skip cover it for now.
