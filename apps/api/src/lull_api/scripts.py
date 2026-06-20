"""Script assembly.

ponytail: deterministic template stub for Sprint 0 — assembles a script from chosen components so
the pipeline is end-to-end runnable. Sprint 1 replaces `build_script` internals with the hardened
LLM call + moderation pass (see docs/PRD.md FR-G4/FR-G5); the signature stays put.
"""

from __future__ import annotations

from dataclasses import dataclass

# Minimal seed library. "ai" lets the assembler pick the first (sensible default) option.
COMPONENTS: dict[str, dict[str, str]] = {
    "induction": {
        "progressive_relaxation": "Let your attention settle on your breath, and with each exhale "
        "let the muscles of your body soften, one by one, from the crown of your head down to your "
        "feet.",
        "fixation": "Find a single point ahead of you and rest your gaze there, letting everything "
        "at the edges of your vision grow soft and distant.",
        "breath_counting": "Breathe in slowly for four, hold for four, and release for six. With "
        "each round, allow yourself to grow a little heavier, a little calmer.",
    },
    "deepener": {
        "staircase": "Imagine a gentle staircase descending. With each step down — ten, nine, "
        "eight — you drift twice as deep, twice as relaxed.",
        "countdown": "I'll count from five to one, and with each number you sink further into calm. "
        "Five… four… three… two… one.",
    },
    "body": {
        "calm_presence": "In this quiet place, you are safe, and there is nothing you need to do. "
        "You can simply rest here, held and at ease.",
        "self_compassion": "Notice a warmth growing in your chest — a gentle kindness toward "
        "yourself, exactly as you are, in this moment.",
    },
    "ending": {
        "gentle_emergence": "In a moment I'll count up from one to five, and you'll return feeling "
        "rested and clear. One… two… three… four… five. Eyes open, fully awake.",
        "drift_to_sleep": "There is nowhere to be and nothing to wake for. Let this calm carry you "
        "down, softly, into sleep.",
    },
}

_CATEGORY_ORDER = ["induction", "deepener", "body", "ending"]


@dataclass
class TrackSpec:
    induction: str = "ai"
    deepener: str = "ai"
    body: str = "ai"
    ending: str = "ai"
    hypnosis: bool = True  # False => plain meditation framing


def _resolve(category: str, choice: str) -> tuple[str, str]:
    """Return (resolved_choice, text). 'ai' picks the first option for the category."""
    options = COMPONENTS[category]
    if choice == "ai":
        choice = next(iter(options))
    if choice not in options:
        raise ValueError(f"unknown {category} option: {choice!r}")
    return choice, options[choice]


def build_script(spec: TrackSpec) -> tuple[str, dict[str, str]]:
    """Assemble script text and the resolved component choices (so 'ai' picks are revealed)."""
    resolved: dict[str, str] = {}
    parts: list[str] = []
    opener = (
        "Make yourself comfortable, and when you're ready, let your eyes gently close."
        if spec.hypnosis
        else "Settle into a comfortable position, and let your attention come to the present moment."
    )
    parts.append(opener)
    for category in _CATEGORY_ORDER:
        choice, text = _resolve(category, getattr(spec, category))
        resolved[category] = choice
        parts.append(text)
    return "\n\n".join(parts), resolved
