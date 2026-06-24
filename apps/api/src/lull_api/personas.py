"""Voice personas (US-005/FR-V1).

The raw ElevenLabs voice ids live here, server-side only, mapped from the stable persona ids the
client knows (packages/shared VOICE_PERSONAS). That indirection is the whole point: the underlying
voice can be re-cast without breaking a user's saved preference, and the client never handles a raw
voice id. Keep the keys in sync with VOICE_PERSONAS.
"""

from __future__ import annotations

# persona id -> ElevenLabs premade voice id.
PERSONA_VOICE_IDS: dict[str, str] = {
    "aria": "9BWtsMINqrJLrRacOk9x",
    "sarah": "EXAVITQu4vr4xnSDxMaL",
    "charlotte": "XB0fDUnXU5powFXDhCwa",
    "james": "JBFqnCBsd6RMkjVDRZzb",
    "daniel": "onwK4e9ZLuTAKqWW03F9",
    "lily": "pFZP5JQG7iQjIQuC4Bku",
}

# A fixed sample read for the per-persona preview (FR-V2): slow, warm, hypnosis cadence (the
# ellipses pace it), ~25s. Same text for every persona so previews compare voices, not scripts.
PREVIEW_TEXT = (
    "Take a slow breath in... and let it go. Allow your shoulders to soften, "
    "and your eyes to rest. With each breath, you are sinking a little deeper... "
    "calm, and warm, and safe. There is nothing you need to do right now... "
    "nowhere to be. Just this gentle quiet, holding you. Let my voice carry you "
    "down, softly, into stillness."
)


def resolve_voice_id(persona_id: str) -> str | None:
    """ElevenLabs voice id for a persona, or None if the id is unknown (caller maps that to 4xx)."""
    return PERSONA_VOICE_IDS.get(persona_id)
