# Lull *(working codename — not final)*

Wellness app that generates personalized self-hypnosis / meditation audio tracks from
user-chosen components (AI script + ElevenLabs voice), built for long, uninterrupted,
customizable sessions — including ketamine-assisted therapy (KAP) and psychedelic-assisted
contexts that mainstream apps refuse to support.

> **Positioning:** wellness / self-help. No medical claims. Not a substitute for clinical care.

## Status
Discovery complete. See [`docs/PRD.md`](docs/PRD.md) for the full product requirements.

- **MVP:** Track Builder + Player (Sprints 0–2)
- **Stack:** Expo / React Native (TS) · FastAPI · BetterAuth · PostgreSQL
- **Audio:** pre-generate + cache via a pluggable `AudioSource` layer

## Docs
- [`docs/PRD.md`](docs/PRD.md) — product requirements
- [`docs/ROADMAP.md`](docs/ROADMAP.md) — sprints + risk gates
- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — stack, pipeline, data model
- [`docs/NAMING.md`](docs/NAMING.md) — naming & domain research (name deferred)
