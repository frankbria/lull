# ElevenLabs Commercial ToS — Cached Audio (Risk Gate P[0.1.3])

**Question (gate):** Does ElevenLabs permit us to pre-generate, **cache**, and serve TTS
audio to Lull's end users on a commercial basis?

**Short answer:** **Yes — with conditions.** Output is ours to keep and serve, provided
Lull runs on a **paid plan** and our usage + end-user terms comply with the Prohibited
Use Policy. This memo cites the controlling clauses, pins the ToS versions, and records
cost-at-scale.

> ⚠️ Not legal advice. This is an engineering reading of the public terms. A shipping
> risk gate needs a human countersign — see [Sign-off](#sign-off) at the bottom.

## Pinned ToS versions

Retrieved **2026-06-20** from elevenlabs.io. We are bound by the non-EEA Terms unless
the account holder resides in the EEA/UK/Switzerland.

| Document | Applies to | Last Updated | URL |
|---|---|---|---|
| Terms of Service (non-EEA) | US / rest-of-world | **31 March 2026** | https://elevenlabs.io/terms-of-use |
| Terms of Service (EU) | EEA / UK / Switzerland | **31 March 2026** | https://elevenlabs.io/terms-of-use-eu |
| Prohibited Use Policy | all users | **3 September 2025** | https://elevenlabs.io/use-policy |

Re-check these dates before any major launch; ElevenLabs changes terms with notice and
"continued use confirms acceptance."

## Is caching + serving to end users permitted?

Yes. The relevant clauses (non-EEA ToS, 31 Mar 2026):

- **§4(c)(ii) — You own the Output.** "Except as expressly set forth herein, as between
  you and ElevenLabs, you retain all rights in and to your Output." Generated audio is
  ours; nothing requires it to be ephemeral, so **storing/caching it is permitted**.
- **§2(a) — Use Output outside the Services.** ElevenLabs "may enable you to download
  Output… you are permitted to use such Output outside of the Services" subject to the
  Terms + Prohibited Use Policy. Serving cached files to our users is such a use.
- **§1(c) — Commercial use requires a paid plan.** Free Users "may only use the Services
  for non-commercial purposes"; Paid Users "may use the Services for commercial
  purposes." **→ Lull must be on a paid subscription.** A business email may also be
  required (a personal email is mandated only for non-commercial use).

### Conditions we must honor

From the **Prohibited Use Policy** (3 Sep 2025):

- **(n) B2B2C floor.** We may not make Output available to our end users "on terms that
  are less restrictive or more permissive than the terms under which our Services and
  their Output have been made available to" us. → **Lull's end-user terms must be at
  least as restrictive as ElevenLabs' ToS + Use Policy** (no resale of the audio, no
  impersonation, etc.).
- **(b) No reselling the Service.** We can't sell/sublicense ElevenLabs' *Services*
  without written authorization — but this "does not preclude your use of Output in
  accordance with the applicable terms." Selling a *product that contains* the audio is
  fine; reselling API access is not.
- **(c) Sound Effects carve-out — N/A.** Standalone resale is barred only for the *Sound
  Effects* product. Lull uses **Text-to-Speech** (`eleven_multilingual_v2`, see
  `apps/api/src/lull_api/audio.py`), so this does not apply. Do not ship Sound Effects
  output as standalone files.
- **No-exclusivity caveat (§10).** Output "may not be unique across users." Acceptable
  for hypnosis tracks; don't market audio as exclusive.

## Tier + cost-at-scale

Commercial use ⇒ **paid plan required**. API rates (elevenlabs.io/pricing/api, retrieved
2026-06-20):

Any paid tier grants commercial-use rights (§1(c)); they differ only in included quota
and concurrency. **Lull is on Starter (~$5/mo, current)** — sufficient for launch; move up
as render volume grows.

| Plan | Price/mo | TTS model used by Lull |
|---|---|---|
| **Starter (current)** | **~$5** | `eleven_multilingual_v2` |
| Creator | $22 | `eleven_multilingual_v2` |
| Pro | $99 | `eleven_multilingual_v2` |
| Scale | $299 | `eleven_multilingual_v2` |

Per-1K-character TTS rates (same across tiers; included quota differs):

| Model | $/1K chars |
|---|---|
| Multilingual v2/v3 (**Lull's current model**) | **$0.10** |
| Flash / Turbo | $0.05 |

**Cost per 90-minute track.** A 90-min hypnosis track is mostly paced silence, so actual
narration is sparse (~18k–25k spoken characters):

- Multilingual v2 @ $0.10/1K → **$1.80 – $2.50 / track** ✅ (matches the gate estimate)
- Flash/Turbo @ $0.05/1K → $0.90 – $1.25 / track (cheaper, if quality is acceptable)

Because audio is **hash-and-cached**, this is a one-time cost per unique script — repeat
plays are free. Switching to Flash/Turbo roughly halves first-render cost.

## Sign-off

Risk gate cleared once a human confirms the reading above:

- [x] Confirmed: pre-generating + caching audio for end users is permitted (this memo)
- [x] ToS versions pinned (table above)
- [x] Tier + cost-at-scale recorded (~$1.80–2.50 / 90-min track on Multilingual v2)
- [x] Action item: Lull on a **paid** ElevenLabs plan before any commercial launch
- [x] Action item: end-user terms ≥ as restrictive as ElevenLabs' ToS + Use Policy

Signed-off-by: Frank H Bria  Date: Jun 20, 2026
