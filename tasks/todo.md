# US-006 — Cost/time estimate + Confirm and Generate (#13)

Self-authored plan (issue had no implementation plan comment).

## Acceptance criteria
- [ ] Modal shows est. chars, duration, generation time before audio
- [ ] Must tap "Confirm and Generate" (not just "Generate")
- [ ] Progress states (script → voice → finalize); clear error + retry on failure

## Key facts
- Estimates already exist: `POST /script` returns `char_count`, `est_seconds`, `est_cost_usd`. No API change needed.
- Flow today: build → preview (ScriptPreview fetches `/script`, scroll-≥50% gate) → "Continue to audio" → `proceedToAudio` → `synthesizeAndPlay` (guest token → `/tts` → play).
- Mobile-only change. React Native's built-in `Modal` (no new dependency).

## Steps (TDD)
1. **New `ConfirmGenerateModal.tsx`** — native `Modal`. Shows: estimated characters (`char_count`), estimated length (`formatDuration(est_seconds)`), estimated generation time (client heuristic). Buttons: Cancel + **Confirm and Generate** (`testID="confirm-generate"`). Owns status: `idle → generating → error`; on confirm runs passed `onGenerate(report)`, displaying progress steps (script → voice → finalize). On failure shows error + **Retry**.
2. **Generation-time estimate** — exported helper `estimateGenerationSeconds(charCount)` with a `ponytail:` comment naming the heuristic + tuning path.
3. **`audio.ts`** — add optional `onProgress?: (stage: "script" | "voice" | "finalize") => void` to `synthesizeAndPlay`; report `script` (claim guest token), `voice` (POST /tts), `finalize` (decode/play).
4. **`TrackBuilderScreen.tsx`** — thread `onProgress` through `proceedToAudio(scriptText, onProgress?)`.
5. **`ScriptPreview.tsx`** — unlocked "Continue to audio" opens the modal instead of synthesizing directly; modal's `onGenerate` calls `onProceed(script, report)`. Error/retry handled in the modal.
6. **Tests** — new `confirmGenerateModal.test.tsx` (estimates shown, confirm triggers generate, progress stages, error+retry). Update `scriptPreview.test.tsx`: unlocked press opens modal (no direct `onProceed`); relocate the audio-error assertion into the modal flow.

## Design decisions / assumptions
- Keep the US-004 scroll gate; "Continue to audio" opens the estimate modal — the modal's "Confirm and Generate" is the explicit generate tap the AC requires.
- "Generation time" is a new client-side estimate (server doesn't return it). Rough heuristic, marked ponytail, tune against real ElevenLabs latency.
- Progress stages map to the existing pipeline; "script" is brief (script is pre-generated) — covers the guest-token/prepare step.
- No persistence/Track-model work (out of scope for this AC).

## Verify
- [ ] `cd apps/mobile && pnpm exec jest` green; `pnpm run lint` + `pnpm run typecheck` clean
- [ ] Demo each AC (Phase 11)
