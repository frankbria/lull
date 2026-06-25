"""Track persistence + audio dedup cache (US-008 / issue #15).

A generated render is saved account-scoped (Track + TrackComponent rows) with its audio metadata
(AudioFile). Audio bytes are written to disk named by a content checksum, so an identical
(script, voice) render is served from that file instead of re-billing TTS.
"""

from __future__ import annotations

import hashlib
import os
import tempfile
import uuid
from pathlib import Path

from sqlalchemy.orm import Session

from .models import AudioFile, Track, TrackComponent


def script_checksum(text: str, voice_id: str | None, source: str) -> str:
    """Stable dedup key over the exact rendered (text, voice, source). The same script in a different
    voice — or rendered by a different audio source (stub vs elevenlabs) — is different audio, so both
    are part of the key. sha256 hex fits AudioFile.checksum (String(64))."""
    h = hashlib.sha256()
    # NUL delimiters so field boundaries can't be ambiguated, e.g. (voice="a", text="bc") collide
    # with (voice="ab", text="c").
    h.update(source.encode("utf-8"))
    h.update(b"\x00")
    h.update((voice_id or "").encode("utf-8"))
    h.update(b"\x00")
    h.update(text.encode("utf-8"))
    return h.hexdigest()


def store_audio(audio: bytes, checksum: str, ext: str, store_dir: str) -> str:
    """Write the bytes under {checksum}.{ext} and return the path. Atomic: write to a temp file in
    the same dir then os.replace into place, so a concurrent /tts that sees cache_path.exists() never
    reads a half-written file. Idempotent — concurrent misses for the same render write identical
    bytes, so the final replace is a harmless last-write-wins."""
    # Resolve to absolute so the path persisted in the DB is portable: a later cache-hit's
    # Path(path).exists() check must not depend on the server's CWD at request time.
    directory = Path(store_dir).resolve()
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{checksum}.{ext}"
    fd, tmp_name = tempfile.mkstemp(dir=directory, suffix=f".{ext}.tmp")
    try:
        with os.fdopen(fd, "wb") as tmp:
            tmp.write(audio)
        os.replace(tmp_name, path)  # atomic on the same filesystem
    except OSError:
        Path(tmp_name).unlink(missing_ok=True)  # don't leave a stray temp file on failure
        raise
    return str(path)


def persist_track(
    db: Session,
    *,
    user_id: uuid.UUID,
    spec: dict,
    components: dict[str, str],
    persona_id: str | None,
    audio_path: str,
    checksum: str,
    duration_seconds: float,
    source: str,
) -> Track:
    """Save an account-scoped track with its metadata (AC2): components, voice, duration, hypnosis
    flag, and date. The voice lives in spec JSONB (persona_id); created_at (date) is server-defaulted;
    ai_chosen per component is recovered from the original spec ('ai' picks). Flushes but does not
    commit — the caller owns the transaction."""
    track = Track(
        user_id=user_id,
        spec={**spec, "persona_id": persona_id},
        status="ready",
    )
    db.add(track)
    db.flush()  # assign track.id for the child rows
    for category, choice in components.items():
        db.add(
            TrackComponent(
                track_id=track.id,
                category=category,
                choice=choice,
                ai_chosen=spec.get(category) == "ai",
            )
        )
    db.add(
        AudioFile(
            track_id=track.id,
            path=audio_path,
            checksum=checksum,
            duration_seconds=duration_seconds,
            source=source,
        )
    )
    return track
