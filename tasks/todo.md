# US-004 — Script preview before audio (scroll ≥50%) — Issue #11

## Acceptance criteria
- [ ] "Generate" produces script **text first, not audio** (≥16pt, scrollable)
- [ ] Shows estimated duration
- [ ] Regenerate script without changing components
- [ ] Cannot proceed to audio until scrolled ≥50%

## Context
- Pure **mobile** feature. API `POST /script` already returns script text + `est_seconds` (no API change).
- Single-screen MVP, no router. State in `TrackBuilderContext` (selections + hypnosis).
- `Sprint0Harness` (__DEV__-only) already proves the script+tts+play path.

## Scope decision (the one real boundary)
Generate sends `{ ...DEFAULT_SPEC, hypnosis }` — every component on `"ai"` plus the real
hypnosis toggle — exactly the contract the API fully supports today (the harness uses it).
**Wiring the per-component assembled spec into Generate is #13 (Confirm & Generate)**, which
also grows the API component library + real LLM (#14). Documented in Known Limitations.
Rationale: keeps US-004 (preview + scroll gate) decoupled from #13 and avoids 500s on catalog
ids the stub doesn't know. No silent fallbacks added.

## Plan
1. **`src/ScriptPreview.tsx`** (new, production component)
   - "Generate script" → `POST /script` with `{...DEFAULT_SPEC, hypnosis}`; sets script state.
   - Script in a bounded scrollable area, `fontSize: 18` (≥16pt), readable lineHeight.
   - Estimated duration from `est_seconds` (formatted `m:ss` / `~N sec`).
   - "Regenerate" → re-`POST /script`; selections/hypnosis untouched (components unchanged).
   - "Continue to audio" disabled until scroll progress ≥50%; calls `onProceed` when enabled.
   - Scroll progress from ScrollView `onScroll` **and** `onContentSizeChange`/`onLayout` so a
     short script that fits on screen unlocks immediately (≥50% already visible).
2. **`src/TrackBuilderScreen.tsx`** — add a `phase` ("build" | "preview") `useState` swap
   (no router — YAGNI). Builder gets a "Generate script" CTA → preview; preview has
   "← Back to track" (components preserved via context). `onProceed` reuses the audio path.
3. **Audio handoff** — extract the harness's tts+play into `src/audio.ts`
   `synthesizeAndPlay(apiBase, scriptText)`; `Sprint0Harness` and ScriptPreview both call it.
   Keeps "Continue to audio" a real action with no duplicated code.
4. **`src/__tests__/scriptPreview.test.tsx`** (new, RNTL + mocked `fetch`)
   - Generate shows script text + duration, and does **not** call `/tts` (script first).
   - "Continue to audio" disabled initially → enabled after `fireEvent.scroll` past 50%.
   - Short script (fits, `onContentSizeChange`) → enabled without scrolling.
   - "Regenerate" re-calls `/script`; selections unchanged.

## Verify
- `cd apps/mobile && npm run test && npm run lint && npm run typecheck`
- Demo (Showboat) every AC with outcome evidence.

## Out of scope (separate issues)
- Per-component assembled spec into Generate — **#13**
- Real LLM script generation — **#14**
- On-device audio playback hardening — **#24**
