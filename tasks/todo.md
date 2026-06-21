# P[0.1.6] CI pipeline (GitHub Actions) — Issue #6

## Acceptance criteria
- [ ] On PR: api `ruff` + `pytest`; mobile `tsc` typecheck + lint
- [ ] Green required to merge; pipeline idempotent
- [ ] Caches uv + pnpm for speed

## Adapted plan (monorepo: pnpm workspace + uv Python api)

1. **Mobile lint/typecheck scripts** (DONE locally, verified passing)
   - Added devDeps `eslint@^9` + `eslint-config-expo` to `apps/mobile`
   - `apps/mobile/eslint.config.js` (Expo flat config)
   - `apps/mobile` scripts: `typecheck` = `tsc --noEmit`, `lint` = `eslint .`

2. **Root `packageManager` field** -> `pnpm@10.27.0` so `pnpm/action-setup` auto-detects.

3. **`.github/workflows/ci.yml`** — `on: pull_request` + `push: main`, with `concurrency`
   (cancel stale runs = efficient + idempotent). Two independent jobs:
   - **api** (`working-directory: apps/api`): `astral-sh/setup-uv` (enable-cache -> caches uv)
     -> `uv sync` -> `uv run ruff check .` -> `uv run pytest -q`
   - **mobile**: `pnpm/action-setup` -> `actions/setup-node` (`node-version-file: .nvmrc`,
     `cache: pnpm`) -> `pnpm install --frozen-lockfile` -> `pnpm --filter mobile typecheck`
     -> `pnpm --filter mobile lint`
   - Jobs kept independent so follow-on #33 can drop in an `eas update` job on merge to main.

4. **Branch protection** ("green required to merge") is a GitHub repo setting, not code.
   Note it in the PR; offer to set via `gh api` (needs admin).

## Out of scope (YAGNI)
- EAS Build / OTA (#33), deploy jobs, matrix builds, coverage gates.
