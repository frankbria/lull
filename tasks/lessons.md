# Lessons

## Mobile device verification (from #24)
Physical-device testing flushes out bugs headless checks never will — treat the device run as a
real gate, not a formality. What it surfaced and the patterns to keep:

- **Audio container must match the source.** The harness hardcoded WAV; live ElevenLabs returns
  MP3. Always derive the player's file extension + MIME from the `/tts` `Content-Type`, never assume.
- **pnpm + Expo needs `nodeLinker: hoisted`** (`pnpm-workspace.yaml`). Without it, SDK 54's
  `@expo/cli` can't resolve `metro-runtime` and bundling dies. Also declare transitive runtime deps
  explicitly (`@babel/runtime`, `expo-constants`) — pnpm's isolated layout won't expose them.
- **Expo Go is always the latest SDK.** Pin the project to the current SDK or the phone refuses to
  open it. Bumping SDK ⇒ check API moves (e.g. `expo-file-system` → `/legacy` in 54) and the Node
  floor (RN 0.81 needs Node ≥20.19.4 — declare `engines`).
- **Browsers need API CORS; native (RN/Expo Go) does not.** "Failed to fetch" on web = CORS;
  "Network error" on device = connectivity/URL, NOT CORS. Diagnose from the API access log: if no
  request from the phone's IP arrives, it's a wrong base URL or unreachable host.
- **Derive the API base from the Metro host** (`Constants.expoConfig.hostUri`) instead of relying on
  `EXPO_PUBLIC_*` env inlining — env vars get baked into stale bundles and silently fall back to
  `localhost` (= the phone itself).
- **`REACT_NATIVE_PACKAGER_HOSTNAME` is an env var, invisible in `ps`/argv.** Don't conclude it's
  unset from the process command line — read `/proc/<pid>/environ`.
- **Tailscale on Android drops in the background** (battery optimization). A "can't load project"
  swirl is often just the phone offline on the tainet — verify with `tailscale ping` from the dev
  box before chasing code. Disable battery optimization for Tailscale.
- **A fresh bundle needs a full app close in Expo Go**, not a reload — reload reuses stale JS.

## Process
- When an issue is pure device/human verification, do every headless proxy first (typecheck,
  bundle, API contract, real request logs), then hand a precise runbook for the human-only part.
  Bring evidence, not just questions.
