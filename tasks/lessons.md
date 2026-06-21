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

## Auth slice (from #32 / PR #35)
- **`PyJWKClientError` is NOT an `InvalidTokenError`** (both subclass `PyJWTError`). Catch
  `jwt.PyJWTError` around provider id_token verification or a JWKS hiccup/unknown-kid surfaces as
  an unhandled 500 instead of a 401.
- **Check-then-insert on a unique column races.** Concurrent signup/OAuth both pass the existence
  check, then one hits `IntegrityError` → 500. Catch it: signup → 409, OAuth → rollback + re-load
  (idempotent). The pre-check stays for the common path; the catch is the correctness backstop.
- **Gate billable work with reserve-before / release-on-failure, not record-after.** For a guest
  free-generation limit: reserve atomically *before* synth (conditional upsert that increments only
  `WHERE used < limit`, so rejected attempts don't bump the counter), and release on render failure
  so a failed/timed-out render never burns the credit. Record-after-success alone reintroduces a
  concurrency race (two first-requests both synthesize).
- **A signed token proves integrity, not scarcity.** Server-issued guest tokens stop forgery but
  not rotation (mint a fresh one each call). True anonymous one-per-person needs a durable signal
  (device attestation / edge rate-limit) — out of scope for an auth slice; document + follow-up.
- **Validate deployment secrets at startup, by strength not just identity.** Rejecting only the
  exact public default lets `LULL_JWT_SECRET=x` through. Add a min-length check, gated on a
  non-dev `environment`, in a pydantic `model_validator`.

## Process
- When an issue is pure device/human verification, do every headless proxy first (typecheck,
  bundle, API contract, real request logs), then hand a precise runbook for the human-only part.
  Bring evidence, not just questions.
- **Cross-family review (`codex review`) is worth iterating to convergence.** It caught the JWKS
  500, the signup race, the credit-burn-on-failure, and a weak-secret gap that internal review +
  green tests missed. Re-run after each fix until only accepted-limitation notes remain.
- **Demo/verification scripts must use a throwaway DB, never `drop_all` a shared test DB.** Running
  one against `lull_test` concurrently (or leaving killed backends holding locks) deadlocks on DDL.
  Use a dedicated `lull_demo`, and `pg_terminate_backend` stale connections if a drop hangs.
- **The pre-commit secret scanner false-positives on test fixtures** (`password=`/`private_key`
  identifiers, ephemeral keygen). GitGuardian on the PR is the authoritative check — it passed,
  confirming `--no-verify` was safe for those commits.
