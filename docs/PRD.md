# Product Requirements Document — "Lull" *(working codename — TEMP, not final name)*

| | |
|---|---|
| **Status** | Draft v0.1 — discovery output, pre-build |
| **Owner** | Frank Bria |
| **Last updated** | 2026-06-20 |
| **Source** | `/home/frankbria/.claude/plans/i-want-to-create-shimmying-cray.md` |
| **Public name** | TBD — deferred to before Sprint 6. Candidates + domain research in [`NAMING.md`](NAMING.md) |

> **One-line:** A wellness app that generates personalized self-hypnosis and meditation audio
> tracks from user-chosen components (AI script + ElevenLabs voice), built for the long,
> uninterrupted, customizable sessions that existing apps refuse to support.

---

## 1. Problem & opportunity

People using self-hypnosis and meditation — especially those in **ketamine-assisted therapy (KAP)**
or other psychedelic-assisted contexts — are poorly served by existing apps:

- **Over-restrictive:** fixed track lengths, forced "emergence"/wake-up endings, no support for the
  long quiet "in-medicine" window a KAP session needs.
- **No psychedelic-context awareness:** none model route-of-administration onset timing or the
  "don't pull me out for 60 minutes" requirement.
- **Locked-down customization:** opinionated defaults the user can't override; the app decides for
  you instead of with you.

**Opportunity:** a tool that *embraces* these contexts as a wellness aid, keeps every component
option always available, learns the user's preferences to *recommend* (never to *restrict*), and is
genuinely hands-off ("set it and forget it") for long unattended sessions.

## 2. Vision

The user opens the app, describes or assembles the session they want, and gets a custom track
voiced in their chosen persona — for a 15-minute daytime reset or a 90-minute KAP session with the
correct onset buffer and a no-emergence medicine window. They press play, the phone goes quiet, and
nothing pulls them out unless *they* reach for it. Over time the app remembers what worked.

## 3. Goals & non-goals

### Goals
- Generate high-quality, **safe** personalized hypnosis/meditation audio on demand.
- Total user control over track composition, with smart defaults and never-locked options.
- Reliable, uninterrupted playback of long sessions, including offline.
- A trustworthy emergency/panic path.
- Eventually: KAP timing engine, scheduling, AI chat builder, owned music catalog.

### Non-goals
- **Not** a medical device. No diagnosis, treatment, dosing, or therapeutic-outcome claims.
- **Not** a substitute for clinical supervision; the app never instructs anyone to take a substance.
- **Not** a clinician/practitioner platform (no HIPAA covered-entity posture). Individual users only.
- **Not** a music-streaming client (no third-party catalog playback in MVP).

## 4. Target users

- **The self-directed wellness user** — uses meditation/self-hypnosis daily; wants depth and
  customization mainstream apps don't allow.
- **The KAP patient (in a supervised, prescribed program)** — needs session audio that matches their
  medicine window, onset, and ending preference; self-identifies as in a clinical program (gated).
- **The psychedelic-curious / integration user** — uses audio for set-and-setting and integration,
  outside or alongside medicine, with no clinical program.

All are **18+**, English-first at launch.

## 5. Positioning & guardrails

- **Wellness / self-help framing everywhere user- and store-facing.** KAP features are described
  externally as **"extended session planning."** Emergency features are **"your own contacts."**
- No store listing, screenshot, name, or copy uses "ketamine," "psychedelic-assisted," or
  drug-facilitation language (App/Play policy risk — see §10).
- All hypnosis content is suggestion/relaxation only — never medical, never dosing.

### 5.1 Strategic context — telehealth integration *(affects later phases + marketing, NOT MVP scope)*

The app is intended as a **differentiating bonus for a telehealth business** that connects patients
to providers for peptides and — more relevantly — **ketamine for mental health**. No competitor can
match a prescriber that *also* ships a tailored KAP session companion (at least not quickly). This is
the **moat and the retention/marketing engine**, not just a standalone app.

Implications to plan around (none change the MVP build):
- **The KAP "supervised, prescribed program" the app gates on (FR-O2) can literally be our own
  telehealth program** — tight, native funnel: prescribe → app → guided session → outcomes.
- **Compliance fork:** once the same entity prescribes *and* provides session software, the
  "arm's-length wellness app" posture weakens and the **business is likely a HIPAA covered entity**.
  Keep the app **legally and architecturally separable** (no PHI flows into the app backend by
  default) so we can choose deliberately between (a) keeping the app a standalone wellness product or
  (b) integrating it as a clinical adjunct with full HIPAA/BAA controls. Don't accidentally couple them.
- **Side features (later):** provider connection, session-bundled-with-prescription, opt-in outcome
  sharing back to the prescriber (HIPAA-gated), integration scheduling tied to dosing.
- **Marketing:** lead the telehealth offer with the app as the unmatched bonus; the app's own store
  listing still stays wellness-framed and store-safe (§10 risk 1 unchanged).

## 6. Scope

**MVP (Sprints 0-2): Track Builder + Player.**
Build a track spec → AI script → preview → ElevenLabs voice → cached audio → safe, uninterrupted,
resumable playback with auto-DND and a panic button. Plus the safety/onboarding that makes it
ethical to ship (Sprint 3 is a hard gate before any real-user exposure).

**Post-MVP (Sprints 4-7):** library/personalization, KAP timing engine, monetization + store
distribution, iOS port. Scheduling/reminders and AI-chat builder slot in around Sprints 4-5.

Full sprint roadmap lives in the approved plan; this PRD details MVP requirements.

## 7. Functional requirements — MVP

### 7.1 Track Builder
- **FR-B1** Four component categories — **Induction, Deepener, Body/Suggestion, Ending** — each with
  ≥5 named, one-line-described options.
- **FR-B2** Exactly one selection per category; selections persist across navigation; a summary card
  shows all four before proceeding.
- **FR-B3** Each category offers an **"AI Choice"** option (default for first-time users), visually
  distinct; the AI's actual pick is revealed in the script preview; any AI Choice is overridable
  per-component without disturbing the others.
- **FR-B4** Prominent **True Hypnosis ↔ Plain Meditation** toggle with a one-sentence explainer each;
  state feeds the generation prompt and is saved as a preference.

### 7.2 Script generation & safety
- **FR-G1** "Generate" produces **script text first, not audio**, in a scrollable ≥16pt preview with
  estimated duration (word-count/pace).
- **FR-G2** User can regenerate the script (new variation) without changing components.
- **FR-G3** User **cannot proceed to audio until they have scrolled ≥50%** of the script.
- **FR-G4** The script-generation **system prompt is versioned and hardened**: no dosages, no
  diagnosis, no therapeutic-outcome promises; resistant to injection via the suggestion-theme field.
- **FR-G5** Every generated script passes a **content-moderation check before TTS**; prohibited
  content (self-harm, named meds beyond user input, age-inappropriate, delusion-reinforcing) blocks
  generation with a safe message.
- **FR-G6** Enforce a **hard character cap** on script length; show estimated cost/time and require an
  explicit **"Confirm and Generate"** before the ElevenLabs charge.

### 7.3 Voice
- **FR-V1** Voice **persona** picker (≥6 personas: name + descriptor), abstracted from raw ElevenLabs
  voice IDs so the underlying voice can be swapped without breaking preferences.
- **FR-V2** 20-30s **preview clip per persona in hypnosis cadence** (slow, warm) — not generic demos.
- **FR-V3** Simplified **warmth** and **pace** controls (mapped to ElevenLabs params).
- **FR-V4** Persona/settings saved as preference; changing voice after generation triggers re-render.

### 7.4 Player & session safety
- **FR-P1** Distraction-free player: track name, elapsed/total, progress, play/pause; no ads or
  recommendations during playback; screen dims after a configurable timeout.
- **FR-P2** **Auto-DND** engages at session start (with a first-run permission request + rationale)
  and **restores the user's prior DND state** on exit; graceful fallback warning if denied.
- **FR-P3** **Headphone disconnect → immediate pause**, no auto-resume; visible "session paused" prompt.
- **FR-P4** **Resumable sessions** — playback position written to disk every ~10s; after a crash/OS
  kill, offer "Resume?" within 5s of the interruption point, or save as a partial session.
- **FR-P5** **Lock-screen controls** (pause + panic) via a foreground media service; survives screen lock.
- **FR-P6** **Low-battery handling:** warn at 20%, countdown at 10%, graceful save-and-end at 5%
  (no abrupt cut).
- **FR-P7** Pre-flight check before start: storage space, audio fully downloaded + **checksum valid**,
  DND capability, battery warning.

### 7.5 Panic button
- **FR-S1** Persistently visible during playback, including when the screen is dimmed.
- **FR-S2** Activated by a deliberate **2-second long-press** (no single-tap triggering).
- **FR-S3** On activation: confirmation screen with pre-configured trip-sitter, national crisis line,
  and 911 options.
- **FR-S4** Calls placed through the **native dialer (not in-app VoIP)**; contact stored **locally**;
  works in **airplane mode / low signal / DND / locked screen**.
- **FR-S5** If no contact configured, show the national crisis line only.

### 7.6 Accounts & data
- **FR-A1** Email/password + OAuth via BetterAuth; **18+ age gate** at account creation.
- **FR-A2** **Guest mode:** one free generation before account creation (conversion + privacy).
- **FR-A3** Generated tracks saved to backend + local cache, account-scoped from day one.
- **FR-A4** Account deletion + data export (GDPR/CCPA).
- **FR-A5** **Entitlement abstraction** (`hasAccess(feature)`) and generation-credit tracking present
  from MVP even though everything is free at launch (so pricing is a config change later).

### 7.7 Onboarding & consent (Sprint 3 — hard gate before real users)
- **FR-O1** Flow: welcome → **intake questionnaire** (screens contraindications: psychosis/
  schizophrenia spectrum, seizure disorders, acute suicidality, dissociative disorders) → **scrollable
  informed consent** (separate from ToS) → age gate → account creation.
- **FR-O2** **KAP-specific consent** gates all KAP features; requires the user to affirm they are in a
  supervised, prescribed program.
- **FR-O3** **Crisis-resource screen** reachable from settings and from within any session; shown as a
  fallback if acute distress is disclosed at intake.
- **FR-O4** Attorney-reviewed **privacy policy** (names AI/voice providers + what data they receive)
  and **ToS** integrated into onboarding.

## 8. Later-phase feature catalog (for roadmap, not MVP)

- **Library & personalization:** save/name/search, metadata, favorites, **per-component
  re-generation**, pre/post **mood check-in delta**, recommendation engine v1, cross-device sync,
  "play again / play similar."
- **KAP timing engine:** total-duration + route-of-administration selector (IV ~30s … oral
  ~10-15min onset); auto-assembly intro → deepener → body → **~60-min no-emergence medicine window**
  → ending; drift-to-sleep vs scheduled-wake endings; timeline preview before generation.
- **Owned music catalog:** Frank's **original compositions + AI-generated beds (ElevenLabs Music)** —
  no licensing/royalties, full control of loopability and KAP no-emergence beds. Beds are tagged data
  behind the `AudioSource` layer; MVP ships a small seed set tagged by mood/context. Third-party
  streaming (Spotify/YouTube/SoundCloud) is a low-priority optional later workstream.
- **Scheduling & reminders;** **AI-chat builder** ("scope or full-build a track" — depends on the
  builder existing underneath).
- **Accessibility audit;** **monetization** (Play Billing, freemium paywall after first free track);
  **iOS port.**

## 9. Architecture sketch

- **Client:** Expo / React Native (TypeScript, strict). Android foreground media service +
  MediaSession (Sprint 2, not retrofitted). Local audio cache + position store.
- **Backend:** FastAPI (Python, `uv`), BetterAuth, **PostgreSQL**.
- **Pipeline:** client → backend generation endpoint → LLM (script) → moderation pass → ElevenLabs
  (voice) → cached audio file (device + cloud).
- **`AudioSource` abstraction:** a single interface fronts all audio (ElevenLabs cached now; real-time
  TTS, music beds, third-party streams later) so provider/source swaps are data, not rewrites.
- **Hosting:** Hostinger dev VPS for staging — check shared-VPS port conflicts and CORS before first
  remote deploy.

### Data model (initial)
`User`, `Track` (spec + status), `TrackComponent` (category, choice, AI-chosen flag), `AudioFile`
(path, checksum, duration, source), `SessionLog` (position, partial flag, rating), `MusicBed`
(tags, loop points), `Entitlement` / `GenerationCredit`.

## 10. Risk gates / compliance (must clear before dependent work)

1. **App/Play store policy (CRITICAL)** — store-safe language; KAP UI not built until policy stance
   confirmed; keep a sideload/PWA fallback. → cleared: [`app-store-policy-stance.md`](app-store-policy-stance.md).
2. **Attorney-reviewed consent + privacy policy (BLOCKER)** — health-adjacent + psychedelic context;
   not a generic template.
3. **Panic-path reliability (catastrophic if it fails)** — verified on real devices in airplane mode,
   DND, locked screen.
4. **ElevenLabs cost + ToS** — char cap, preview-before-render, hash-and-cache, confirm caching is
   permitted and pin the ToS version. (~$1.80-2.50 per 90-min track; budget the scale curve.)
5. **AI content safety** — moderation pass + legal review of 20-30 sample scripts pre-launch.
6. **Android foreground-service kills (Samsung OneUI)** — correct implementation + battery-exemption
   guidance; validate on Samsung/Pixel/Xiaomi.

## 11. Non-functional requirements
- **Offline-first playback** of fully-downloaded tracks; no mid-session network dependency.
- **Reliability:** a 90-min session must not be dropped by OS battery optimization; recover position.
- **Privacy:** PII stripped from AI calls; no session-content in analytics (metadata only); documented
  retention + deletion.
- **Accessibility:** screen-reader labels on all controls, large-text/high-contrast, thumb-zone panic,
  state-change haptics, script transcript. (Full audit Sprint 7; build in from the start.)
- **Cost control:** char cap + preview + cache; per-user generation tracking.

## 12. Success metrics (MVP)
- A track can be built, previewed, generated, and played end-to-end on a real Android device.
- 90-min session completes unattended on Samsung/Pixel/Xiaomi without service kill or data loss.
- Panic long-press dials a configured number in airplane mode, 100% of test runs.
- Zero moderation-bypassing harmful scripts in a 50-script red-team set.
- (Engagement metrics — completion rate, return rate, mood delta — instrumented for post-MVP.)

## 13. Open questions
- LLM provider/model for script generation (Claude default per stack) and moderation approach
  (separate model call vs rules + classifier).
- Exact ElevenLabs tier and whether enterprise pricing is needed before launch.
- Public name + domain (deferred workstream).
- Whether guest-mode generation is cached server-side at all (privacy vs conversion).
- iOS panic/DND constraints (Focus mode API is more restricted than Android) — validate in Sprint 7 planning.

## 14. Appendix — MVP user stories
Eleven Sprint 1-2 stories with acceptance criteria (US-001…US-011) are specified in the approved
plan and become the seed GitHub issues for the Builder, Generation, and Player epics.
