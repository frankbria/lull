# Issue #4 — P[0.1.4] Confirm App Store / Play policy stance for positioning

**Type:** risk-gate (decision/docs). Blocks building KAP UI. Mirrors the ElevenLabs ToS gate (#3 → `docs/elevenlabs-commercial-tos.md`).

## Acceptance criteria → deliverable mapping
- [ ] Written go/no-go on wellness framing → memo "Short answer" + sign-off
- [ ] No KAP/psychedelic language in store metadata plan → banned-terms + approved-framing table
- [ ] Sideload/PWA fallback decision recorded → fallback section

## Plan (docs-only)
1. **New doc** `docs/app-store-policy-stance.md` — go/no-go memo, ElevenLabs-doc format:
   - Gate question + short answer (**GO** on wellness framing, with conditions)
   - Pinned policy versions (Apple App Store Review Guidelines; Google Play Marijuana / Illegal Activities; retrieved 2026-06-20)
   - Analysis: Lull neither sells nor facilitates sale of controlled substances and gives no dosing → Apple **1.4.3** & Google **Marijuana** policy don't bite; not a medical app but honor Apple **1.4.1/1.4.2** disclaimer posture
   - Store-metadata language rule: banned terms vs approved framing ("extended session planning", "your own contacts")
   - **Sideload/PWA fallback decision**: Android APK sideload + installable PWA as plan-B if Play rejects; iOS fallback = PWA / EU alt-marketplace
   - Sign-off checklist mapping the 3 ACs + human countersign line
2. **Update** `docs/ROADMAP.md` risk gate #1 → link new doc, mark cleared (mirror gate #4 row).
3. **Update** `docs/PRD.md` §10 risk 1 → link new doc.

## Out of scope
No code. No store-listing copy yet (Sprint 6). Not legal advice — human countersign required.

## Process
branch `docs/p0-1-4-store-policy-stance` → write → pre-commit → PR → demo (AC checklist) → merge.
