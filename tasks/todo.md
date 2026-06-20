# Issue #1 — P[0.1.1] Initialize Expo mobile app & run Sprint-0 harness

**Plan source:** self-authored (issue had AC, no detailed implementation plan).
**Branch:** `feat/1-expo-mobile-init`

## Adapted plan
1. Create feature branch off `main`.
2. `cd apps/mobile && npx expo install` — let Expo reconcile SDK 52 dependency versions; commit the
   resulting `package.json` changes + `pnpm-lock.yaml`.
3. Resolve anything `expo install` / `npx expo-doctor` flags (version mismatches, peer deps).
4. Make the Sprint-0 harness **web-runnable** so the `/script`→`/tts` round-trip can be demo-verified
   headlessly: branch the audio write path (`expo-file-system` is native-only) to use a Blob URL on
   web. Keeps native path unchanged.
5. Confirm/extend `EXPO_PUBLIC_API_BASE` documentation (emulator `10.0.2.2` / LAN IP) in README + a
   `apps/mobile/.env.example`.
6. Typecheck (`tsc --noEmit`) passes.

## Acceptance criteria
- [ ] `npx expo install` reconciles SDK 52 deps — **verifiable here**
- [ ] App boots on an Android device/emulator — **device-only; user verifies**
- [ ] "Generate & play" calls `/script` then `/tts` and audio plays — **round-trip verifiable here; audible playback device-only**
- [ ] `EXPO_PUBLIC_API_BASE` documented for emulator (10.0.2.2) / LAN IP — **verifiable here**

## Demo-gate note
Two ACs (device boot, audible playback) cannot be evidenced in this environment. Resolution chosen
in Phase 4 below.
