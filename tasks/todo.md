# Issue #55 — Public HTTPS API, Tailscale-free APK (P[0.1.7a])

**Resolved direction:** self-managed **Hostinger VPS** (s878435) — Docker + Caddy (auto Let's
Encrypt TLS) + Postgres; CI deploys over SSH on merge to main. Compiled APK targets a public
`https://api.<domain>` — no Tailscale.

## Repo-side deliverables (me — verifiable locally)
1. `apps/api/Dockerfile` — build the API image (uv, src, uvicorn). Verify: `docker build`.
2. `apps/api/docker-compose.prod.yml` — services: `api`, `caddy` (reverse proxy/TLS), `db` (Postgres,
   if bundled). Volumes: caddy certs, `audio_store`, pg data. Verify: `docker compose config`.
3. `apps/api/Caddyfile` — `{$API_DOMAIN} { reverse_proxy api:8000 }` (auto HTTPS).
4. `.github/workflows/deploy-api.yml` — on push to main touching `apps/api/**`: rsync/ssh to VPS →
   `docker compose -f docker-compose.prod.yml up -d --build` → `alembic upgrade head` → `/health` probe.
   Secrets: `DEPLOY_SSH_KEY`, `DEPLOY_HOST`, `DEPLOY_USER`; var: `API_DOMAIN`.
5. Per-profile `EXPO_PUBLIC_API_BASE`: set EAS `preview`/`production` env + GH var to
   `https://api.<domain>`; dev stays Metro-derived. Remove the Tailscale value.
6. CORS: document/set `LULL_CORS_ORIGINS` for the prod web origin.
7. Docs: deploy runbook (DNS, secrets, first deploy, migrations, rollback).

## User-provided (provisioning — can't be done from the repo)
- **Public domain/subdomain** (e.g. `api.lull.app`) + DNS A-record → VPS public IP.
- Confirm the shared VPS can run **Docker** and **80/443 are free** (port-conflict check).
- SSH deploy: create a deploy key, add pubkey to VPS `authorized_keys`, add privkey + host + user as
  GH secrets.
- Host secrets: `LULL_JWT_SECRET`, `LULL_ANTHROPIC_API_KEY`, `LULL_ELEVENLABS_API_KEY`,
  `LULL_DATABASE_URL` (or bundled Postgres), `LULL_SCRIPT_SOURCE=claude`, `LULL_AUDIO_SOURCE=elevenlabs`.
- Decide Postgres: **bundled** (compose `db`) vs managed.

## Defaults (correct me)
Docker + Caddy + bundled Postgres (all consistent with the existing `docker-compose.yml`).

## Verification (split)
- Me: `docker build` succeeds, `docker compose config` valid, workflow lints, `/health` in a local
  compose-up.
- You: real deploy on the VPS + on-device APK check against the public URL.
