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

## EAS Build + OTA (from #33)
- **SDK < 56 monorepos need an explicit `apps/mobile/metro.config.js`.** Without it the EAS cloud
  bundle anchors to the pnpm **workspace root** (no `main` field) and falls back to
  `expo/AppEntry.js` → `import '../../App'` → "Unable to resolve module ../../App". It builds fine
  *locally* (your hoisted `node_modules` masks it), so this only surfaces in the cloud. Fix:
  `getDefaultConfig(__dirname)` + `watchFolders=[workspaceRoot]` + `nodeModulesPaths=[app, workspace]`.
  Auto-config landed in SDK 56; until then the file is mandatory. (`nodeLinker: hoisted` is necessary
  but not sufficient.)
- **Pull EAS cloud logs without the browser:** the build page renders logs client-side, but the
  Expo GraphQL API (`https://api.expo.dev/graphql`, header `expo-session: <state.json sessionSecret>`)
  exposes `builds.byId(...).{error, logFiles}`. The `logFiles` URLs are **brotli**-compressed — decode
  with python `brotli.decompress`. Reproduce the failing phase locally with the same command the log
  shows (`expo export:embed --eager --platform android --dev false`), run from the repo root to mimic
  the cloud's workspace-root anchoring.
- **Running `eas`/`expo` from the repo root litters root-level `app.json`/`eas.json` defaults** (with
  a *different* auto-package like `com.frankbria.lull`). Run them from `apps/mobile`; if stray root
  configs appear, delete them before committing.
- **`runtimeVersion: fingerprint` + `eas update --channel` (not `--branch`)** is the safe OTA combo:
  native changes auto-bump the runtime so installed builds never pull an incompatible JS bundle.
- **Release Android blocks cleartext HTTP** — a standalone APK can't reach a plain-`http://` dev API
  (Tailscale box). Needs HTTPS (e.g. `tailscale serve`) or dev-only `expo-build-properties`
  `usesCleartextTraffic` (never production).

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
- **Don't ship a dev/test harness as a visible affordance in a feature screen.** #8 kept the
  Sprint-0 "Generate & play" (posts `DEFAULT_SPEC`) under the new track builder; codex flagged it
  as a misleading way to "proceed" since it ignores the user's selections. Gate such harnesses
  behind `__DEV__` — keeps the device-testing loop in dev, out of production builds.
- **Async-hydrated state (AsyncStorage) has two traps: a load can clobber a fast user edit, and
  it warns under `act(...)` in tests.** US-003's persisted toggle defaults in `useState`, then a
  mount effect overrides from storage. Fixes: (1) a `userSetRef` set in the setter so the async
  load skips `setState` once the user has chosen — kills the clobber for free, no extra state;
  (2) have `loadHypnosis()` return `boolean | null` (null = nothing stored) so cleared-storage
  tests dispatch no update at all → no `act` warnings, default lives once in `useState`. Resist a
  `hydrated` flag to gate a __DEV__-only harness button: it fires `setState` on every mount,
  reintroducing warnings suite-wide to defend a race a human can't win against a ~1ms read.

## Script-preview scroll gate (from US-004 / #11)
A web/RNTL demo + cross-family review caught three things unit tests alone missed:

- **"Scrolled ≥50%" means scroll *position*, not *visible fraction*.** First cut unlocked when
  `(offsetY + viewportH) / contentH ≥ 0.5`, so a script only slightly taller than its box showed
  ≥50% at the top and unlocked with **zero** scrolling. Gate on `offsetY / (contentH - viewportH)`
  instead; treat `contentH ≤ viewportH` (fits entirely) as already-unlocked so short scripts don't
  trap. The live demo is what exposed it — the math "looked right" in tests.
- **Nested vertical `ScrollView` needs `nestedScrollEnabled` on Android.** An inner scroll area
  inside the screen's outer `ScrollView` won't scroll (or fire `onScroll`) on Android without it —
  the 50% gate would never unlock on a real device though web worked fine.
- **Re-gate by remounting the inner ScrollView (`key={generation}`).** `onContentSizeChange` only
  fires when the size *changes*; regenerating a same-height script otherwise leaves the gate stuck.
  Bumping a `key` forces fresh layout/content-size callbacks and resets scroll to top.
- **`toHaveTextContent("...")` is exact-match here, not substring** — use a regex
  (`toHaveTextContent(/2:10/)`) to assert a fragment.
- **Async press handlers must catch.** A `Pressable` calling an async `onProceed` un-awaited leaks
  unhandled rejections; wrap in `Promise.resolve(onProceed(...)).catch(setError)` and serialize the
  handoff with an in-flight ref so rapid taps can't orphan a player.

## US-005 — Voice persona selection + preview (#12)
- **An ungated public endpoint that triggers a paid call needs a cost cap, and the cap must hold
  under concurrency.** A simple result-cache still lets a burst of concurrent *cold* requests each
  fire the billable call. Cache the in-flight `asyncio.Task` (single-flight) so overlapping callers
  share one synthesis — store the task *before* the first `await`.
- **Caching an `asyncio.Task` needs failure + cancellation eviction or it poisons the cache.**
  `await task` directly lets a cancelled request cancel the *shared* task, and `CancelledError` is a
  `BaseException` that `except Exception` won't catch. Use `await asyncio.shield(task)` for request
  awaits, and evict via `task.add_done_callback` checking `t.cancelled() or t.exception()` — a
  done-callback covers every exit path.
- **Any "store the cleanup after an await" pattern races against state changing mid-flight.** A
  synth/preview that resolves after the user changed the voice (or unmounted) would store/play a
  stale player. Capture a token (or `mounted` ref) before the await; if it changed when the promise
  resolves, run the returned cleanup immediately and don't store it.
- **A dev DB one migration behind 500s the whole gated path.** `guest_credits` wasn't applied to
  the dev `lull` db, so every `/tts` 500'd in the live demo though all tests (isolated, migrated
  test DB) passed. Run `alembic upgrade head` on the dev DB before a live API demo; an env-state
  500 looks like a code bug until you read the traceback (`relation ... does not exist`).
- **The persona abstraction is a deliberate client/server split:** public `{id,name,descriptor}` in
  `@lull/shared`, secret `id→voice_id` map server-only — same pattern as the component catalog
  (mobile `catalog.ts` ↔ api `scripts.py`). `loadVoice` drops a stored id no longer in the catalog
  so a removed persona falls back to the default instead of 422-ing `/tts`.

## Credit/cache boundaries (from #15 / US-008)
- **Reserve→work→refund must guard EVERY exit path, including `asyncio.CancelledError`.** The guest
  free generation is reserved+committed before the (slow) render, so any later failure must refund
  it. `except Exception` is not enough: `CancelledError` (client disconnect mid-render) is a
  *BaseException* and slips past it — add an explicit `except asyncio.CancelledError` that refunds.
  Same reason `_preview_cache` evicts via a done-callback. Wrap the whole render/persist/commit span
  in one guard; a mapped synth error keeps its HTTP status, `OSError`→503, anything else refunds and
  re-raises unmasked.
- **A global on-disk cache needs per-test isolation or tests flake.** Once `/tts` always writes a
  content-addressed file to `audio_store/`, tests that assert "synthesis ran" get false cache hits
  from earlier tests. Fix with an autouse conftest fixture pointing `settings.audio_store_dir` at a
  fresh `tmp_path` per test — never the repo default.
- **Dedup cache key must hash the EFFECTIVE render inputs, not the request's raw ones.** Keying on
  `voice_id` (None for the default-voice path) serves stale audio after the configured default
  changes; key on the resolved voice + the audio source. Persist component metadata from the
  server-side resolution of the spec, never client-supplied values (which can contradict the spec).
