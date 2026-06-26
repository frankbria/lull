#!/usr/bin/env bash
# Dev-only (#54): serve the API over HTTPS on the tailnet so a standalone Android APK — which blocks
# cleartext http — can reach it. Runs uvicorn on loopback and fronts the port with `tailscale serve`,
# which terminates TLS at https://<this-host>.<tailnet>.ts.net and proxies to the local API.
#
# This is the *interim* dev loop. The durable, Tailscale-free path (a public HTTPS API the compiled
# APK targets directly) is #55 (P[0.1.7a]) — do not ship this for production.
#
# Usage:  bash scripts/dev-tls.sh            # front TLS + run uvicorn (Ctrl-C tears the front down)
#         bash scripts/dev-tls.sh --check    # dry run: print the commands, run nothing
set -euo pipefail

# Loopback: `tailscale serve` proxies the tailnet HTTPS endpoint to http://127.0.0.1:$PORT, so the
# device reaches uvicorn *through* the TLS front. Binding 0.0.0.0 would needlessly expose the API in
# cleartext on every other interface (LAN, etc.), bypassing that front.
HOST="127.0.0.1"
PORT="${LULL_DEV_PORT:-8000}"
APP="lull_api.main:app"

uvicorn_cmd=(uv run uvicorn "$APP" --host "$HOST" --port "$PORT" --reload)
serve_cmd=(tailscale serve --bg "$PORT")          # https://<host>.ts.net -> http://127.0.0.1:$PORT
serve_off=(tailscale serve reset)                 # supported teardown; clears serve config

if [[ "${1:-}" == "--check" || "${1:-}" == "--dry-run" ]]; then
  printf 'dev-tls (dry run) — would run, in order:\n'
  printf '  %s\n' "${serve_cmd[*]}"
  printf '  %s\n' "${uvicorn_cmd[*]}"
  printf '  (on exit) %s\n' "${serve_off[*]}"
  printf '  (aborts up front if a tailscale serve config already exists)\n'
  exit 0
fi

command -v tailscale >/dev/null 2>&1 || { echo "error: tailscale CLI not found on this dev box" >&2; exit 1; }
command -v uv >/dev/null 2>&1 || { echo "error: uv not found" >&2; exit 1; }

# This helper owns the tailnet serve for the session. If ANY serve config already exists (HTTPS, TCP,
# or otherwise), bail instead of clobbering it — `tailscale serve --bg` would replace the handler, and
# the `reset` teardown clears ALL serve config. We only ever start (and therefore only ever reset) when
# there was nothing else to lose. Detect via --json so a non-HTTPS config is caught too (empty config
# prints "null"/"{}").
existing_serve="$(tailscale serve status --json 2>/dev/null || true)"
if [[ -n "$existing_serve" && "$existing_serve" != "null" && "$existing_serve" != "{}" ]]; then
  echo "error: a tailscale serve config already exists on this node — refusing to overwrite it." >&2
  echo "  clear it ('tailscale serve reset') or front the API yourself, then re-run." >&2
  exit 1
fi

cleanup() { echo; echo "tearing down tailscale serve…"; "${serve_off[@]}" 2>/dev/null || true; }
trap cleanup EXIT

echo "fronting :$PORT with TLS via tailscale serve…"
"${serve_cmd[@]}"
tailscale serve status || true
echo "starting uvicorn on $HOST:$PORT (Ctrl-C to stop)…"
"${uvicorn_cmd[@]}"
