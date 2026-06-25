"""Post-generation content-moderation pass (FR-G5 / issue #14 AC2).

Every generated script runs through `moderate()` BEFORE it is sent to TTS. Prohibited content blocks
generation with a safe message instead of being voiced.

ponytail: a rules/keyword classifier — deterministic, offline, and exactly what the ≥50-script
red-team needs to assert zero bypasses against. The PRD leaves "separate model call vs rules +
classifier" open (open question §10); this is the rules baseline. Upgrade path: add an LLM/classifier
pass in front of these rules when the keyword set stops keeping up — the call site doesn't change.
"""

from __future__ import annotations

import re

# Medications we never want voiced unless the user named them themselves (the "named meds beyond user
# input" rule). Not exhaustive by design — the upgrade path is a maintained list or a classifier.
_MEDICATIONS = (
    "xanax",
    "prozac",
    "valium",
    "ativan",
    "ambien",
    "adderall",
    "zoloft",
    "lexapro",
    "klonopin",
    "oxycodone",
    "vicodin",
    "fentanyl",
    "benzodiazepine",
    "ssri",
    "lithium",
    "seroquel",
)

# Shared fragments. A count is a digit or a spelled-out small number; the med alternation lets the
# dosage rule catch "take two Xanax" (dosing a NAMED med is never allowed, even one the user named —
# the user exemption only excuses *mentioning* a med, never *dosing* it).
_COUNT = r"(?:\d+|a|one|two|three|four|five|six|several|some|another|a\s+few)"
_UNIT = r"(?:mg|mcg|ml|milligrams?|micrograms?|milliliters?)"
# Class terms pluralize ("SSRIs", "benzodiazepines"); brand names don't, so only these need aliases.
_MED_TERMS = _MEDICATIONS + ("ssris", "benzodiazepines")
_MED_ALT = "|".join(re.escape(m) for m in _MED_TERMS)

# category -> patterns. First matching category wins; the category name is surfaced to the caller.
_RULES: dict[str, tuple[re.Pattern[str], ...]] = {
    "self_harm": (
        re.compile(r"\b(kill|harm|hurt|cut|hang|suffocate)\s+yourself\b"),
        re.compile(r"\b(end|take)\s+your\s+(own\s+)?life\b"),
        re.compile(r"\bsuicid"),
        re.compile(r"\b(overdose|over-dose)\b"),
        re.compile(r"\bno\s+reason\s+to\s+(live|go on)\b"),
        re.compile(r"\bbetter\s+off\s+dead\b"),
        re.compile(r"\bworld\s+would\s+be\s+better\s+without\s+you\b"),
    ),
    # Dosage instructions: a number (digit or spelled out) adjacent to a medical unit, a dose noun,
    # or a named medication.
    "dosage": (
        re.compile(rf"\b{_COUNT}\s?{_UNIT}\b"),
        re.compile(rf"\btake\s+{_COUNT}\s+(pills?|tablets?|capsules?|doses?|drops?)\b"),
        # "take <med>" with or without a count/article — instructing to take a med is never allowed.
        re.compile(rf"\btake\s+(?:{_COUNT}\s+|your\s+)?(?:{_MED_ALT})\b"),
        re.compile(r"\b(double|increase|skip)\s+your\s+(dose|dosage|medication)\b"),
    ),
    "diagnosis": (
        re.compile(
            r"\byou\s+(have|are\s+suffering\s+from|suffer\s+from)\s+"
            r"(?:[a-z]+\s+){0,3}"  # allow modifiers/articles: "severe", "generalized", "a clinical"
            r"(depression|anxiety|bipolar|ptsd|ocd|adhd|insomnia|panic\s+disorder|trauma|"
            r"disorder|illness)\b"
        ),
        re.compile(r"\byou\s+are\s+(clinically|medically)\s+\w+"),
        re.compile(r"\b(i|we)\s+diagnose\s+you\b"),
        re.compile(r"\byour\s+diagnosis\s+is\b"),
    ),
    "outcome_promise": (
        re.compile(r"\b(will|guaranteed\s+to|is\s+guaranteed\s+to)\s+cure\b"),
        re.compile(
            r"\b(cure|heal|fix)s?\s+your\s+(depression|anxiety|disease|illness|disorder|"
            r"condition|cancer)"
        ),
        re.compile(r"\bpermanently\s+(cure|heal|eliminate)\b"),
        re.compile(r"\bwill\s+eliminate\s+your\s+(depression|anxiety|disease|illness|disorder)"),
        re.compile(r"\bguaranteed\s+(cure|recovery|healing)\b"),
        re.compile(r"\bno\s+longer\s+need\s+(your\s+)?(medication|therapy|doctor)\b"),
    ),
    "age_inappropriate": (
        re.compile(r"\b(sexual|sexually|aroused|arousal|orgasm|naked|undress)\b"),
        re.compile(r"\btouch\s+yourself\s+(intimately|sexually)\b"),
    ),
    "delusion_reinforcing": (
        re.compile(r"\byou\s+(can|are\s+able\s+to)\s+(fly|breathe\s+underwater|stop\s+time)\b"),
        re.compile(r"\byou\s+are\s+(invincible|immortal|a\s+god|all-powerful|superhuman)\b"),
        re.compile(r"\byou\s+(don't|do\s+not)\s+need\s+to\s+(eat|drink|breathe|sleep\s+ever)\b"),
        re.compile(r"\bgravity\s+(does\s+not|doesn't)\s+(apply|affect)\b"),
        re.compile(r"\byou\s+(have|possess)\s+(supernatural|magical)\s+powers\b"),
    ),
}


class ScriptModerationError(Exception):
    """A generated script was blocked. `category` names the violated rule; `message` is client-safe."""

    SAFE_MESSAGE = (
        "We couldn't generate a safe script for this request. Please adjust your selections and try "
        "again."
    )

    def __init__(self, category: str) -> None:
        super().__init__(f"script blocked by moderation: {category}")
        self.category = category
        self.message = self.SAFE_MESSAGE


def moderate(script: str) -> None:
    """Raise ScriptModerationError if the script contains prohibited content; return None if clean.

    Fail closed on named medications: a generated/finalized script must never voice a specific drug
    name regardless of what the user typed — so /script and /tts apply the identical rule and a script
    /script approves can never be rejected at /tts. (The generic word "medication" is fine; only the
    specific drug names in `_MEDICATIONS` are blocked.) PII stripping protects the user's *input* from
    being flagged; this protects the *output* from naming drugs.
    """
    lowered = script.lower()

    for category, patterns in _RULES.items():
        for pattern in patterns:
            if pattern.search(lowered):
                raise ScriptModerationError(category)

    for med in _MED_TERMS:
        if re.search(rf"\b{re.escape(med)}\b", lowered):
            raise ScriptModerationError("named_medication")
