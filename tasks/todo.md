# Issue #5 — P[0.1.5] PostgreSQL + initial data model (auth deferred)

**Decisions (user-confirmed 2026-06-20):**
- **Auth runtime = Python-native in FastAPI** (not BetterAuth — it's Node-only and the backend is
  Python). Authlib/passlib/JWT will land in a follow-up. Docs updated to match.
- **Scope split:** this PR = foundational data slice. Auth/OAuth/18+ gate → follow-up issue.

## This PR delivers (subset of #5 AC)
- [x] Postgres provisioned — **local** (docker-compose) + **staging** (`LULL_DATABASE_URL` env)
- [x] Migrations (Alembic) for User, Track, TrackComponent, AudioFile, SessionLog, MusicBed,
      Entitlement, GenerationCredit
- [x] `has_access(feature)` entitlement seam + generation-credit counter (free at launch)
- [ ] BetterAuth email/pw + OAuth + 18+ age gate → **DEFERRED** to follow-up issue (auth slice)

## Stack (minimal, maintained defaults)
SQLAlchemy 2.0 (sync) + `psycopg[binary]` (psycopg3) + Alembic. UUID PKs (`gen_random_uuid()`).

## Steps (TDD: test → impl per step)
1. **Deps + config** — add sqlalchemy/alembic/psycopg to `pyproject.toml`; add `database_url`
   to `Settings`; `db.py` with engine + `SessionLocal` + `Base` + `get_db()` dependency.
2. **Models** — `models.py`: 8 tables per `ARCHITECTURE.md` data model. UUID PKs, FKs, JSON for
   spec/tags. User has email/password_hash(nullable)/age_verified — columns only, no auth logic yet.
3. **Alembic** — init under `apps/api/alembic/`, wire to `LULL_DATABASE_URL`, autogenerate initial
   migration. Test: upgrade→downgrade roundtrip on a real test DB.
4. **Entitlement seam** — `entitlements.py`: `has_access(db, user_id, feature) -> bool` (True,
   free at launch) + `record_generation(db, user_id)` bumps GenerationCredit. ponytail comment +
   upgrade path noted.
5. **Provisioning** — `apps/api/docker-compose.yml` (local Postgres); `.env.example` +
   README "Database setup" section; staging via `LULL_DATABASE_URL`.
6. **Docs** — `ARCHITECTURE.md` + `PRD.md` (FR-A1, §10.2 stack): BetterAuth → "Python-native auth
   (Authlib/passlib/JWT)". Note the deviation.

## Tests (real Postgres, no mocks — docker-compose DB)
- model create + FK integrity (Track→User, TrackComponent→Track, AudioFile→Track, SessionLog→User/Track)
- `has_access` returns True (free at launch); `record_generation` increments counter
- alembic upgrade head → downgrade base roundtrip leaves no tables
- `/health` still green (no regression)

## Out of scope (→ follow-up issue, opened at wrap)
Signup/login endpoints, OAuth providers, 18+ age-gate enforcement, session/JWT, KAP-consent flow.

## Process
branch `feat/p0-1-5-postgres-data-model` → TDD → deslop → quality gate (cross-family review) →
PR (with Known Limitations + deferred-auth note) → demo (AC checklist) → CI → merge → open auth issue.
