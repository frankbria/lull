# Issue #8 — P[1.1.1] US-001 Build a track by selecting components

**Scope**: mobile-only (area:mobile). Selection UI + summary card. Generation/"proceed"
is owned by #13 (Confirm & Generate) and #14 (real LLM) — NOT this story.

## Acceptance Criteria
- [ ] All four categories (induction, deepener, body, ending) render, ≥5 named options each + one-line description
- [ ] Exactly one selection per category; persists across navigation (survives screen remount)
- [ ] Summary card shows all four before proceeding

## Design decisions
- **Catalog** in `apps/mobile/src/catalog.ts` (mobile-local; the API COMPONENTS dict has only
  2–3/category and syncing it is #13/#14's concern). 4 categories × 5 options = `{id, name, blurb}`.
  Reuse existing API ids where they exist; add the rest. ponytail-comment the API gap.
- **State** via a small React Context (`TrackBuilderContext`) holding the 4 selections + setters.
  Provider wraps the app → selections survive screen unmount/remount = "persists across navigation".
  No nav library (YAGNI — single screen; real multi-screen flow lands with later stories).
- **Existing sprint-0 generate-and-play** harness is preserved (device testing keeps working),
  rendered below the builder, still using DEFAULT_SPEC. Assembled-spec generation = #13.

## Files
- `apps/mobile/src/catalog.ts` — CATEGORIES + options (the only new "data")
- `apps/mobile/src/TrackBuilderContext.tsx` — provider + `useTrackBuilder()` hook
- `apps/mobile/src/CategorySection.tsx` — one category, single-select rows
- `apps/mobile/src/SummaryCard.tsx` — shows the 4 chosen names
- `apps/mobile/src/TrackBuilderScreen.tsx` — sections + summary (+ kept harness)
- `apps/mobile/App.tsx` — wrap in provider, render screen
- Test runner: add `jest-expo` + `@testing-library/react-native`, jest config, `test` script
- CI: add `pnpm --filter mobile test` step (idempotent)

## TDD steps
1. RED: tests — 4 categories render w/ ≥5 options; single-select per category; summary shows all 4;
   selection persists across remount (Context).
2. GREEN: catalog → context → components → screen → App wiring.
3. REFACTOR + deslop, lint, typecheck, coverage ≥85%.
4. Demo every AC (Phase 11), open PR, CI + review gates, merge.
