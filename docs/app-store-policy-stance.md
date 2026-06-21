# App Store / Play Policy Stance — Positioning (Risk Gate P[0.1.4])

**Question (gate):** Can Lull ship through the Apple App Store and Google Play under a
**wellness/self-help** positioning, given its KAP / psychedelic-adjacent purpose — and what
language and fallback must we lock so store review doesn't reject or pull the app?

**Short answer (go/no-go):** **GO — under wellness framing, with conditions.** The store rules
that actually reject apps in this space target *facilitating the sale of* or *encouraging
consumption of* controlled substances. Lull does **neither**: it sells no substance, arranges no
sale, and gives no dosing or "how to take it" instruction — it generates relaxation/meditation
audio. The genuine risk is **adjacency** (a reviewer associating the app with drug use via its
copy), which the wellness-framing guardrail in [`PRD.md`](PRD.md) §5 is built to manage. We hold
the line on store-facing language and keep a sideload/PWA escape hatch. **KAP UI stays unbuilt
until this gate is signed (it now is).**

> ⚠️ Not legal advice. This is an engineering reading of public developer policies. A shipping
> risk gate needs a human countersign — see [Sign-off](#sign-off).

## Pinned policy versions

Retrieved **2026-06-20**. Both stores treat these as living documents — **re-check before any store
submission** (Sprint 6).

| Document | Store | URL |
|---|---|---|
| App Store Review Guidelines | Apple | https://developer.apple.com/app-store/review/guidelines/ |
| Restricted Content — Illegal Activities / "Marijuana" | Google Play | https://support.google.com/googleplay/android-developer/answer/9878810 |
| Developer Program License / Health misrepresentation | both | store-specific developer agreements |

Apple's guidelines carry no public "last updated" stamp ("a living document… new rules at any
time"). Google revises Play policies on a published rolling schedule with enforcement grace
periods.

## Why wellness framing clears the rules that bite

**The controlling clauses target sale and encouragement — not adjacency.**

- **Apple §1.4.3 (verbatim):** *"Apps that encourage consumption of tobacco and vape products,
  illegal drugs, or excessive amounts of alcohol are not permitted… Facilitating the sale of
  controlled substances (except for licensed pharmacies and licensed or otherwise legal cannabis
  dispensaries), or tobacco is not allowed."* → Lull **encourages no consumption** and
  **facilitates no sale**. It does not bite.
- **Google Play "Marijuana" / Illegal Activities (verbatim):** *"We don't allow apps that
  facilitate the sale of marijuana or marijuana products, regardless of legality."* Violations are
  in-app ordering, arranging delivery/pickup, facilitating THC sales. → Lull does **none**. It does
  not bite. (Ketamine is not cannabis, but Google's drug stance is the same family — *facilitation*
  is the trigger, and we don't.)
- **Apple §1.4.4 / §1.4.5 (physical-harm family):** prohibit apps that *urge* risky behavior. Lull
  urges none; the in-medicine window is paced silence, not instruction.

**Medical-app posture — stay out of it.** Lull is **not** a medical device and makes no
diagnostic/treatment claims (PRD §3 non-goals). To stay clear of the medical-scrutiny rules:

- **Apple §1.4.1 (verbatim):** medical apps *"should remind users to check with a doctor… before
  making medical decisions."* → We are not a medical app, but we **adopt the posture anyway**: a
  "not medical advice / consult a clinician" line in onboarding + content (already required by PRD
  §7.7 consent and §5 guardrails). This is cheap insurance against a reviewer reclassifying us.
- **Apple §1.4.2:** drug-dosage calculators need manufacturer/FDA provenance. → Lull ships **no
  dosing feature**, ever. The KAP timing engine schedules *audio sections* against a user-stated
  onset; it never calculates, recommends, or mentions a dose. Keep it that way.

## No KAP / psychedelic language in the store-metadata plan

Store-facing surfaces = app name, subtitle, description, keywords, screenshots, preview video,
in-app purchase names, and the privacy "nutrition label". **None may contain drug-facilitation or
psychedelic language.** This binds the Sprint-6 listing copy; it is the plan, not the final copy.

| ❌ Banned store-facing | ✅ Approved framing |
|---|---|
| ketamine, KAP, psychedelic(-assisted), trip, journey (drug sense), microdose | "extended / long-form sessions", "deep relaxation", "guided self-hypnosis & meditation" |
| dose, dosing, onset, come-up, in-medicine | "session timing", "set-and-forget length", "uninterrupted window" |
| emergency drug help, trip-sitter, bad trip | "your own contacts", "a person you choose", "support contact" |
| therapy, treatment, clinical, cure, diagnose | "wellness", "self-help", "for your own practice" |

Rules:
- The words above appear **nowhere** user- or store-facing. Internal code/docs may use them.
- No screenshot or preview frame shows banned terms or drug imagery.
- KAP features are described externally **only** as "extended session planning" (PRD §5).
- Emergency/panic features are described **only** as "your own contacts" (PRD §5).
- Run a banned-term grep over listing assets before every submission.

## Sideload / PWA fallback decision

**Decision: maintain a store-independent distribution path as a standing plan-B.** If either store
rejects or later pulls the app over adjacency, we are not dead — we degrade, we don't disappear.

- **Android (primary platform, MVP):** ship-able **off-Play** today — a signed **APK/AAB sideload**
  (direct download or a third-party store such as F-Droid / Samsung Galaxy Store) and an
  **installable PWA** (Chrome "Add to Home Screen" → WebAPK) both work without Google's approval.
  This is a real escape hatch, not a theoretical one. **Action:** keep the build producing a
  standalone signable APK and keep the web target PWA-installable (manifest + service worker) so
  the fallback stays warm — don't let it bit-rot.
- **iOS (Sprint 7 port):** Apple is stricter — no general sideloading. Fallbacks are an
  **installable PWA via Safari "Add to Home Screen"** (works everywhere, reduced background/native
  capability) and, in the **EU only**, an alternative app marketplace / notarized distribution
  under the DMA. Treat App Store approval as the iOS happy path and the PWA as the universal
  iOS fallback; do not gate the MVP on iOS.
- **Consequence for design:** because the PWA fallback must stay viable, avoid hard dependencies on
  store-exclusive services in core flows (e.g. don't make first-run impossible without Play
  Services). Native-only niceties (foreground media service, DND) degrade gracefully on PWA.

## Action items

- [ ] **Sprint 6:** re-pin both policies' current versions before drafting listing copy.
- [ ] **Sprint 6:** banned-term grep over all store-listing assets pre-submission.
- [ ] **Ongoing:** keep a signable standalone APK + installable PWA build green as the fallback.
- [ ] **Ongoing:** no dosing/onset calculation or drug language ever reaches store-facing surfaces.
- [ ] **Sprint 3/6:** "not medical advice / consult a clinician" line carried in onboarding + copy.

## Sign-off

Risk gate cleared once a human confirms the reading above:

- [x] **Go/no-go on wellness framing recorded:** **GO, with conditions** (this memo).
- [x] **Store-metadata plan carries no KAP/psychedelic language** (banned-vs-approved table above).
- [x] **Sideload/PWA fallback decision recorded** (Android APK + PWA primary fallback; iOS PWA / EU
      alt-marketplace).
- [x] Controlling clauses cited + versions pinned (Apple §1.4.1–1.4.5; Google Play "Marijuana").

Signed-off-by: Frank H Bria  Date: Jun 20, 2026
