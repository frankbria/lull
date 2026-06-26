# Deploying the Lull API (#55)

Public HTTPS API on the shared VPS, **no Tailscale dependency** — the compiled app targets
`https://lull.dev.frankbria.net` directly.

## Topology
```
phone / internet ──HTTPS──> nginx (:443, certbot TLS, server_name lull.dev.frankbria.net)
                              └── proxy_pass ──> 127.0.0.1:8020  (uvicorn, in Docker, host networking)
                                                   └── 127.0.0.1:5432  system Postgres (db "lull")
```
- **Container:** `docker-compose.prod.yml` → `lull-api`, `network_mode: host`, uvicorn bound to
  `127.0.0.1:8020` (loopback only — not publicly exposed). Audio cache at `/opt/lull/audio_store`.
- **DB:** the box's system Postgres 16, dedicated `lull` role + `lull` database (per-app convention).
  Reached on `127.0.0.1:5432` — no change to Postgres `listen_addresses`/`pg_hba` (other apps undisturbed).
- **TLS:** existing nginx + certbot. Site at `/etc/nginx/sites-enabled/lull.dev.frankbria.net`
  (template in `deploy/`). Cert auto-renews.
- **Port 8020** chosen because 8000/8005/8010 were already taken on the shared box.

## Secrets — `/opt/lull/.env.prod` (on the box, `chmod 600`, never committed)
```
LULL_ENVIRONMENT=staging            # enforces a real LULL_JWT_SECRET
LULL_JWT_SECRET=<64-hex>            # generated on the box
LULL_DATABASE_URL=postgresql+psycopg://lull:<pw>@127.0.0.1:5432/lull
LULL_AUDIO_SOURCE=stub             # -> elevenlabs to enable real audio (needs the key below)
LULL_SCRIPT_SOURCE=stub            # -> claude to enable real LLM scripts (needs the key below)
# LULL_ELEVENLABS_API_KEY=sk-...
# LULL_ANTHROPIC_API_KEY=sk-ant-...
```
**Enable real audio / scripts:** edit `.env.prod` (set the source + key), then
`cd /opt/lull && docker compose -f docker-compose.prod.yml up -d` (recreates with the new env).

## Manual deploy / update
```bash
# from a machine with the deploy key:
rsync -az --delete --exclude='.venv' --exclude='audio_store' --exclude='.env*' \
  --exclude='__pycache__' --exclude='.pytest_cache' --exclude='.ruff_cache' \
  apps/api/ root@dev.frankbria.net:/opt/lull/
ssh root@dev.frankbria.net 'cd /opt/lull &&
  docker compose -f docker-compose.prod.yml build &&
  docker compose -f docker-compose.prod.yml run --rm api uv run --no-dev alembic upgrade head &&
  docker compose -f docker-compose.prod.yml up -d'
curl -fsS https://lull.dev.frankbria.net/health
```
`.env.prod` and `audio_store/` are excluded from rsync, so deploys never clobber secrets or the cache.

## CI auto-deploy
`.github/workflows/deploy-api.yml` runs the same steps on merge to `main` touching `apps/api/**`.
It is **guarded** — a no-op until all of these repo secrets exist:
- `DEPLOY_SSH_KEY` — private key authorized on the box (use a dedicated deploy key, not a personal one).
- `DEPLOY_HOST` — `dev.frankbria.net` (or the IP).
- `DEPLOY_USER` — `root`.
- `DEPLOY_KNOWN_HOSTS` — pinned host key (no trust-on-first-use). Generate with
  `ssh-keyscan dev.frankbria.net` and paste the output.

## App wiring
`EXPO_PUBLIC_API_BASE = https://lull.dev.frankbria.net` (no trailing slash) — set on the EAS `preview`
environment and the GitHub repo variable (for OTA). Replaces the old Tailscale URL. Dev (Expo Go) still
derives the base from the Metro host.

## Rollback
`docker compose -f docker-compose.prod.yml down` stops it (nginx then 502s the subdomain only — other
sites unaffected). Re-deploy a prior commit to restore. Migrations are forward-only; coordinate
destructive schema changes.
