#!/usr/bin/env bash
# Dev-only (#54): run the API behind `tailscale serve` so a standalone Android APK — which blocks
# cleartext http — can reach it. The tailnet HTTPS endpoint terminates TLS and proxies to
# http://127.0.0.1:$PORT, so the device reaches uvicorn *through* the front.
#
# On the build box `tailscale serve` is typically already running persistently. This script
# COOPERATES with that: it never modifies or resets an existing serve config — it just runs uvicorn
# on the loopback port the serve fronts. It only sets up (and later tears down) a serve when none
# exists, e.g. on a fresh box.
#
# The durable, Tailscale-free path (a public HTTPS API the compiled APK targets directly) is #55
# (P[0.1.7a]) — do not ship this for production.
#
# Usage:  bash scripts/dev-tls.sh            # ensure TLS front + run uvicorn (Ctrl-C stops)
#         bash scripts/dev-tls.sh --check    # dry run: print what it would do, run nothing
set -euo pipefail

# Loopback: `tailscale serve` proxies the tailnet HTTPS endpoint to http://127.0.0.1:$PORT. Binding
# 0.0.0.0 would needlessly expose the API in cleartext on every other interface, bypassing the front.
HOST="127.0.0.1"
PORT="${LULL_DEV_PORT:-8000}"
APP="lull_api.main:app"
uvicorn_cmd=(uv run uvicorn "$APP" --host "$HOST" --port "$PORT" --reload)

if [[ "${1:-}" == "--check" || "${1:-}" == "--dry-run" ]]; then
  printf 'dev-tls (dry run):\n'
  printf '  if a tailscale serve config exists:  leave it untouched (expected to front :%s)\n' "$PORT"
  printf '  if none exists:                      tailscale serve --bg %s  (torn down on exit)\n' "$PORT"
  printf '  always:                              %s\n' "${uvicorn_cmd[*]}"
  exit 0
fi

command -v tailscale >/dev/null 2>&1 || { echo "error: tailscale CLI not found on this dev box" >&2; exit 1; }
command -v uv >/dev/null 2>&1 || { echo "error: uv not found" >&2; exit 1; }

# Cooperate with an already-running serve (the build box's persistent front): leave it alone and never
# reset it. Only when there is NO serve at all do we create one for this session and tear down that one.
existing_serve="$(tailscale serve status --json 2>/dev/null || true)"
if [[ -n "$existing_serve" && "$existing_serve" != "null" && "$existing_serve" != "{}" ]]; then
  echo "tailscale serve already configured — leaving it untouched. Current mapping:"
  tailscale serve status || true
  # Verify it actually proxies to OUR port, so we don't run uvicorn behind a front for something else
  # and falsely "succeed". Heuristic (matches the proxy target in the status/JSON); warn, don't abort,
  # so a detection miss can't block a correctly-configured box.
  if echo "$existing_serve" | grep -qE "(127\.0\.0\.1|localhost):$PORT([^0-9]|$)"; then
    echo "✓ existing serve proxies to :$PORT — good."
  else
    echo "WARNING: the existing serve does not appear to proxy to http://127.0.0.1:$PORT." >&2
    echo "  the APK reaches THIS API only if the tailnet HTTPS host proxies to :$PORT." >&2
    echo "  fix: 'tailscale serve --bg $PORT' (or repoint your serve to :$PORT), then re-run." >&2
  fi
else
  echo "no tailscale serve config found — fronting :$PORT with TLS for this session…"
  tailscale serve --bg "$PORT"
  # Reset only the serve THIS run created (safe: there was none before).
  trap 'echo; echo "tearing down the serve this run created…"; tailscale serve reset 2>/dev/null || true' EXIT
fi

echo "starting uvicorn on $HOST:$PORT (Ctrl-C to stop)…"
"${uvicorn_cmd[@]}"
