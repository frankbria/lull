# US-002 — AI/random per-component, revealed in preview (issue #9)

**Self-authored plan** (issue had no plan comment). Builds directly on US-001's
TrackBuilderContext / CategorySection / SummaryCard.

## What the issue asks
- AC1: Each component has an "AI Choice" — the default for first-time users, visually distinct.
- AC2: The AI's actual pick is revealed in the script preview.
- AC3: AI Choice is overridable per-component without disturbing others.

## Design (lazy)
There is no real LLM yet (#14), so "AI Choice" = the system picks one option at
random per category. The sentinel `"ai"` becomes a valid selection value and the
**default** for every category, so a first-time user starts fully AI-picked.

- `Selections` value goes from `string | null` → `string` (concrete id **or** `"ai"`).
  Default = `"ai"` for all four categories (no more "not chosen" state).
- Provider holds `aiPicks: Record<CategoryId, string>` — the concrete option the AI
  picked per category, computed **once** per provider mount so the preview is stable.
  An optional `aiPicker` prop makes this deterministic in tests (default = random).
- CategorySection renders an "AI Choice" pseudo-option at the top, visually distinct,
  selected by default. The concrete options sit below.
- SummaryCard ("Your track" preview) always shows now; for an AI category it reveals
  the actual picked option name with an "AI Choice" marker. AC3 is already satisfied
  by `select` only touching one key.

## Steps (TDD: tests first)
1. **catalog.ts** — export `AI_CHOICE = "ai"` sentinel.
2. **TrackBuilderContext.tsx** — default selections all `"ai"`; add stable `aiPicks`
   + optional `aiPicker` prop; expose `aiPicks` on context.
3. **CategorySection.tsx** — AI Choice option (distinct style, `testID=option-<cat>-ai`),
   selected when value is `"ai"`.
4. **SummaryCard.tsx** — always render; reveal AI's actual pick + marker for ai rows.
5. **__tests__/trackBuilder.test.tsx** — update US-001 tests for new default; add:
   default is AI for every category; preview reveals the deterministic AI pick;
   overriding one category leaves the others on AI; revert concrete -> AI.

## Verify
`npm test`, `npm run typecheck`, `npm run lint` in apps/mobile — all green.

## Deviations / assumptions
- Self-authored; no plan existed on the issue.
- "Default for first-time users" is read as the in-memory initial state (all AI) —
  no persistence/first-run layer exists yet, so YAGNI.
- "AI" is random per-component until the real LLM lands (#14); stable per session.
- Mobile-local, consistent with US-001 (no API change).
