"""Strip PII from untrusted text before it reaches the LLM / TTS (FR privacy, issue #14 AC3).

ponytail: regex for the high-frequency identifiers (email, phone, SSN) — the realistic vectors in
a free-text suggestion theme. Upgrade path: a NER pass (names, addresses) if themes get richer.
"""

from __future__ import annotations

import re

# Order matters only in that SSN runs before the generic phone pattern can't eat it (different shape).
_EMAIL = re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b")
_SSN = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")
# 10-digit US-style phone numbers. The separated form keeps the last separator required so it doesn't
# swallow ordinary counts ("breathe for 4 seconds"); the unseparated form matches a bare 10-digit run
# (optionally +1), which in a relaxation theme is overwhelmingly a phone number.
_PHONE = re.compile(r"\b(?:\+?1[\s.-]?)?\(?\d{3}\)?[\s.-]?\d{3}[\s.-]\d{4}\b|\b\+?1?\d{10}\b")

_REDACTION = "[redacted]"


def strip_pii(text: str) -> str:
    """Replace emails, SSNs, and phone numbers with a redaction marker."""
    text = _EMAIL.sub(_REDACTION, text)
    text = _SSN.sub(_REDACTION, text)
    text = _PHONE.sub(_REDACTION, text)
    return text
