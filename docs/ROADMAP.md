# Roadmap

Condensed from the approved discovery plan. Full requirements: [`PRD.md`](PRD.md).
~2-week sprints. **Bold gates** must be signed off before dependent sprints start.

| Sprint | Goal | Demoable outcome |
|---|---|---|
| **0 Foundation** | Skeleton that won't need restructuring | ElevenLabs call → cached audio plays in a test harness. **Gate: confirm ElevenLabs ToS + store-policy stance.** |
| **1 MVP Core** | Build a spec → generate audio | Pick components → review script → generate → hear it play |
| **2 Player + Session Safety** | Safe, uninterrupted, recoverable | 20-min track plays through a simulated call from lock screen, no data loss; panic dials a test number. **Gate: foreground service validated on Samsung/Pixel/Xiaomi.** |
| **3 Onboarding + Consent** | Safe for a real user | Install → consent → first track; panic connects. **Gate: attorney review of consent + privacy policy.** |
| **4 Library + Personalization** | The app has memory | Retrieve last week's track, re-generate only the ending, replay |
| **5 KAP Timing Engine** | The differentiator becomes usable | 90-min oral-troche plan shows timeline (onset → no-emergence window → ending), plays with music bed |
| **6 Monetization + Distribution** | Can charge + survive store review | New user → 1 free track → paywall → subscribe → KAP session |
| **7 iOS Port + Polish** | iOS, no architectural change | Full KAP session on iPhone through locked screen; accessibility audit |

Scheduling/reminders and the AI-chat builder slot in around Sprints 4-5. Marketing / final naming /
domain / pricing / social is a separate workstream after a usable MVP (Sprint 6+).

## Risk gates (block shipping)
1. **App/Play store policy** — store-safe language; KAP UI not built until policy stance confirmed; keep sideload/PWA fallback. → [`app-store-policy-stance.md`](app-store-policy-stance.md) ✅ **cleared** (GO on wellness framing with conditions; Lull facilitates no sale and gives no dosing, so Apple §1.4.3 / Play "Marijuana" don't bite; Android APK+PWA fallback held).
2. **Attorney-reviewed consent + privacy policy** — health-adjacent + psychedelic context.
3. **Panic-path reliability** — native dialer, local contact, works airplane/DND/locked-screen; verified on real devices.
4. **ElevenLabs cost + ToS** — char cap, preview-before-render, hash-and-cache, confirm caching permitted + pin ToS version. → [`elevenlabs-commercial-tos.md`](elevenlabs-commercial-tos.md) ✅ **cleared** (caching permitted on a paid plan; signed off, on Starter plan).
5. **AI script content safety** — moderation pass + legal review of sample scripts.
6. **Android foreground-service kills** (Samsung OneUI) — correct impl + battery-exemption guidance.

> Strategic note: the app is the moat/retention bonus for a planned ketamine/peptide **telehealth
> business**. Keep the app legally/architecturally **separable** (no PHI into the app backend by
> default) so clinical integration stays a deliberate choice. See PRD §5.1.
