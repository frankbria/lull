# Issue #54 — Standalone APK can't reach API ("Network request failed") [P[0.1.1c]]

**Plan source:** self-authored. Labels: area:mobile, area:infra, sprint:0, bug.
Scope: unblock the **internal dev-test APK**. Durable fix (public API, no Tailscale) = #55 (P[0.1.7a]).

## Root cause (confirmed)
APK has `https://s878435.tail919ab8.ts.net` baked in, but nothing serves HTTPS there — dev API is
plain `http` on `:8000` with no TLS front; release APK also blocks cleartext. → connection never
completes → "Network request failed". Previews fail the same way (and swallow the error → #56).

## Principle-consistent fix
Do NOT bake Tailscale/cleartext into the APK (that's #55's concern). Instead make the **dev box**
serve HTTPS over the tailnet, and document/automate it. The APK is unchanged.

## Deliverable (repo)
1. **README "Device delivery"**: a dev-TLS runbook — bind uvicorn `0.0.0.0:8000`, front with
   `tailscale serve --bg 8000` (terminates TLS at `https://<host>.ts.net`), the diagnostics
   (`curl -v .../health`, `tailscale serve status`), and the cold-restart-the-APK step.
2. **`apps/api` dev helper** (Makefile target or `scripts/dev-tls.sh`): one command to run uvicorn on
   `0.0.0.0:8000` + start `tailscale serve`, with teardown. Reproducible, no per-run recall.
3. No app code change, no cleartext, APK untouched.

## TDD / checks (light — this is docs + a shell helper)
- Helper script: a `--check`/dry-run mode that prints the exact commands without executing, asserted
  by a tiny test (bind host = 0.0.0.0, serve port = 8000). One runnable check behind the logic.
- Local evidence I CAN produce: uvicorn binds `0.0.0.0:8000` + `GET /health` → 200.

## Demo gate (Phase 11) — split
- ✅ I produce: uvicorn binds 0.0.0.0, `/health` 200 locally; helper emits correct commands.
- 🔲 YOU confirm on-device: cold-restart the APK → "Generate script" returns a script; previews fetch.
  **Merge waits on your device confirmation** (won't merge on CI-green alone).

## Acceptance (from #54)
- [ ] Installed preview APK: "Generate script" returns a script (no "Network request failed"). *(device)*
- [ ] Voice previews fetch successfully. *(device)*
