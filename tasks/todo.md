# P[0.1.7] EAS Build + OTA continuous delivery to test device — Issue #33

## Acceptance criteria
- [ ] `eas.json` + EAS project configured; `expo-updates` added with `runtimeVersion` policy + `updates.url`/channel.
- [ ] One-time dev/preview build installs on the Android device (`eas build --profile preview --platform android`). [HUMAN]
- [ ] App auto-updates on launch — `expo-updates` `checkAutomatically: ON_LOAD`; document foreground-resume behavior.
- [ ] GitHub Actions job: on merge to `main`, `eas update --channel preview` (JS/asset only; native needs rebuild).
- [ ] Channel mapping: `main` → `preview` channel the installed build subscribes to.
- [ ] Idempotent + cached (reuse #6 setup); `EXPO_TOKEN` via secrets, never committed.
- [ ] README "Device delivery" section: one-time install, update flow, native-change caveat.

## Decisions (approved)
- **Repo: PUBLIC** (done — `gh repo edit --visibility public`).
- Device-proven (#24): **yes** — OK to wire OTA.
- EAS project setup done **live this session** via owner's Expo login (`eas init` + `eas update:configure`).

## Plan
1. **Auth** (owner): `npx eas-cli login` (file-based, persists to session).
2. `expo install expo-updates` (SDK-54-aligned version) in apps/mobile.
3. `eas init` → writes `extra.eas.projectId`. `eas update:configure` → `updates.url`, `runtimeVersion` policy, `expo-updates` plugin.
4. `app.json`: `updates.checkAutomatically = "ON_LOAD"`, confirm `runtimeVersion` policy (appVersion or fingerprint).
5. `eas.json`: build profiles `development` / `preview` / `production`, each mapped to a channel; `preview` = internal APK, channel `preview`.
6. `.github/workflows/eas-update.yml`: `on: push: branches:[main]` (+ `paths` JS/asset), checkout (SHA-pinned) → setup-node+pnpm (reuse #6 cache) → `eas update --branch preview --non-interactive --auto`. Guard on `EXPO_TOKEN` (graceful skip like codex-review). `EXPO_TOKEN` via secret.
7. README "Device delivery" section.
8. `gh secret set EXPO_TOKEN` (owner-provided token).

## Demo evidence mapping
- Config ACs: `expo-doctor` / typecheck pass; eas.json + app.json show channel + ON_LOAD.
- Build + device-install + auto-update-on-launch: **HUMAN acceptance step** (owner's Expo account + phone) — document outcome.
- Workflow AC: dry-run / graceful-skip path verified in CI; `eas update` job structure shown.

## Out of scope (YAGNI)
- Store/TestFlight/Play CD (Sprint 6), iOS device delivery (Sprint 7), native-change auto-rebuild pipeline.
