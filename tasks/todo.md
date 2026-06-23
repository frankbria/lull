# US-003 — Hypnosis vs meditation toggle (issue #10)

**Self-authored plan** (no plan comment). Mobile-local, building on the US-001/002 TrackBuilder.

## What the issue asks
- AC1: Prominent toggle, True Hypnosis ↔ Plain Meditation, with a one-sentence explainer each.
- AC2: Feeds the generation prompt; saved as a preference and pre-filled next time.

## Key facts from exploration
- `@lull/shared` `TrackSpec` **already** has `hypnosis: boolean` (the API consumes it; default true).
  So "feeds generation" = the spec sent to `/script` carries the toggle value.
- No persistence library is installed yet — this story introduces one. AsyncStorage is the
  standard, Expo-Go-bundled choice (rung 3: native platform feature).
- The only generation path today is the `__DEV__` Sprint0Harness (assembled-spec generation is #13),
  so that is where the toggle feeds the request for now.

## Design (lazy)
- Hypnosis lives in `TrackBuilderContext` alongside the component selections (`hypnosis` + `setHypnosis`).
- A thin `preferences.ts` wraps AsyncStorage (load/save one key, error-safe, default = true).
- Context loads the saved value on mount and persists on every change → "pre-filled next time".
- A prominent `HypnosisToggle` (two segmented options, each with its explainer) drives it.
- `Sprint0Harness` sends `{ ...DEFAULT_SPEC, hypnosis }` so the toggle actually feeds generation.

## Steps (TDD: tests first)
1. `npx expo install @react-native-async-storage/async-storage` + register its official jest mock.
2. `preferences.ts` — `loadHypnosis()` / `saveHypnosis(v)`, default true, error-safe.
3. `TrackBuilderContext.tsx` — add `hypnosis`/`setHypnosis`; load on mount; persist on change.
4. `HypnosisToggle.tsx` — prominent True Hypnosis ↔ Plain Meditation toggle + explainers.
5. `TrackBuilderScreen.tsx` — render the toggle prominently (above the categories).
6. `Sprint0Harness.tsx` — include `hypnosis` from context in the `/script` body.
7. Tests: default is hypnosis; both modes + explainers render; toggling updates state;
   persistence round-trip (save -> remount -> pre-filled).

## Verify
`npm test`, `npm run typecheck`, `npm run lint` in apps/mobile — all green.

## Deviations / assumptions
- Self-authored; no plan existed on the issue.
- AsyncStorage's official in-memory jest mock is used for the persistence round-trip — it is the
  platform storage layer (a native module absent in node), not our logic, so this respects the
  "real services" rule while staying runnable in CI.
- "Feeds generation" is wired into the existing (dev) generation path; full assembled-spec
  generation is #13. Flagged in Known Limitations.
