from __future__ import annotations

import asyncio
import uuid
from typing import Callable

import jwt
from fastapi import Depends, FastAPI, Header, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from .audio import AudioSource, AudioSourceError, get_audio_source
from .auth import current_user_optional, router as auth_router
from .config import settings
from .db import get_db
from .entitlements import (
    has_access,
    record_generation,
    release_guest_generation,
    reserve_guest_generation,
)
from .models import User
from .moderation import ScriptModerationError, moderate
from .personas import PREVIEW_TEXT, resolve_voice_id
from .pii import strip_pii
from .scripts import (
    ScriptSource,
    ScriptSourceError,
    TrackSpec,
    build_script_source,
    resolve_components,
)
from .security import decode_guest_token

app = FastAPI(title="Lull API", version="0.1.0")
app.include_router(auth_router)

# Browser clients (Expo web, and a future web build) are cross-origin to the API, so the
# preflight needs CORS. Native (Expo Go / RN) ignores CORS. Default opens it for local dev;
# staging/prod restrict via LULL_CORS_ORIGINS.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)


class TrackSpecIn(BaseModel):
    induction: str = "ai"
    deepener: str = "ai"
    body: str = "ai"
    ending: str = "ai"
    hypnosis: bool = True
    # Untrusted suggestion theme (FR-G4); PII-stripped + delimited before the LLM. Capped here so an
    # oversized theme can't bloat the upstream prompt (the char cap elsewhere is output-only).
    theme: str = Field(default="", max_length=500)


class ScriptOut(BaseModel):
    script: str
    char_count: int
    est_seconds: float
    est_cost_usd: float
    components: dict[str, str]  # resolved choices (reveals 'ai' picks — FR-B3)


class TtsIn(BaseModel):
    text: str
    persona_id: str | None = None  # US-005: which voice to render; None => configured default


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "audio_source": settings.audio_source}


def get_script_source() -> ScriptSource:
    """The configured script generator (stub offline, Claude in prod). A config error (claude with no
    key) surfaces as a 503, matching the audio path. Overridable in tests."""
    try:
        return build_script_source(settings)
    except RuntimeError as exc:
        raise HTTPException(
            status_code=503, detail={"message": str(exc), "retryable": False}
        ) from exc


@app.post("/script", response_model=ScriptOut)
async def generate_script(
    spec_in: TrackSpecIn,
    source: ScriptSource = Depends(get_script_source),
) -> ScriptOut:
    """Script first, audio later (FR-G1): returns text to preview + a cost/time estimate.

    Pipeline (PRD §): resolve AI picks -> generate -> moderate BEFORE TTS (FR-G5). A moderation block
    returns a safe 422 so prohibited content is never voiced.
    """
    spec = TrackSpec(**spec_in.model_dump())
    try:
        components = resolve_components(spec)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    try:
        script = await source.generate(spec, components)
    except ScriptSourceError as exc:
        raise HTTPException(
            status_code=exc.status_code, detail={"message": exc.message, "retryable": exc.retryable}
        ) from exc

    try:
        moderate(script)
    except ScriptModerationError as exc:
        raise HTTPException(
            status_code=422, detail={"message": exc.message, "blocked": exc.category}
        )

    chars = len(script)
    if chars > settings.max_script_chars:
        raise HTTPException(
            status_code=422, detail=f"script exceeds {settings.max_script_chars} chars"
        )

    return ScriptOut(
        script=script,
        char_count=chars,
        est_seconds=chars / 12.5,  # ~150 wpm hypnosis pacing
        est_cost_usd=round(chars / 1000 * settings.cost_per_1k_chars_usd, 4),
        components=components,
    )


def get_source_factory() -> Callable[[str | None], AudioSource]:
    """A factory that builds an AudioSource for a given voice id (US-005: persona voices vary per
    request, so the source can't be a single fixed dependency). Config errors surface as a 503."""

    def make(voice_id: str | None = None) -> AudioSource:
        try:
            return get_audio_source(settings, voice_id)
        except RuntimeError as exc:
            raise HTTPException(
                status_code=503, detail={"message": str(exc), "retryable": False}
            ) from exc

    return make


# Each persona's preview (fixed text + fixed voice) is deterministic, so synthesize it at most once
# and serve from memory after — that caps billable ElevenLabs calls on this ungated endpoint to one
# per persona, closing the repeat-request cost vector. We cache the in-flight *task*, not just the
# result, so a burst of concurrent cold requests for the same persona share one synthesis instead of
# each firing their own (single-flight). ponytail: in-process; a shared cache/CDN if multi-instance.
_preview_cache: dict[str, asyncio.Task[tuple[bytes, str]]] = {}


@app.get("/voices/{persona_id}/preview")
async def voice_preview(
    persona_id: str,
    make_source: Callable[[str | None], AudioSource] = Depends(get_source_factory),
) -> Response:
    """A short, fixed sample in the persona's voice (FR-V2). Ungated on purpose: a preview must not
    burn the user's free generation, and the text is server-fixed so it can't be abused for a full
    render. The first hit per persona synthesizes; concurrent and later hits share/reuse it."""
    voice_id = resolve_voice_id(persona_id)
    if voice_id is None:
        raise HTTPException(status_code=404, detail="unknown voice persona")

    task = _preview_cache.get(persona_id)
    if task is None:
        # Store the task BEFORE awaiting so an overlapping request finds and awaits the same one.
        async def render() -> tuple[bytes, str]:
            source = make_source(voice_id)
            return await _synthesize(source, PREVIEW_TEXT), source.media_type

        task = asyncio.ensure_future(render())

        # Evict a task that ends in failure OR cancellation, so a poisoned entry never sticks in the
        # cache until restart. A done-callback covers every exit path, including CancelledError
        # (a BaseException that a try/except Exception around the await would miss).
        def _evict_if_unsuccessful(t: asyncio.Task[tuple[bytes, str]]) -> None:
            if t.cancelled() or t.exception() is not None:
                _preview_cache.pop(persona_id, None)

        task.add_done_callback(_evict_if_unsuccessful)
        _preview_cache[persona_id] = task

    # shield: if THIS request is cancelled (client disconnect), it must not cancel the shared
    # synthesis that other waiters depend on.
    audio, media_type = await asyncio.shield(task)
    return Response(content=audio, media_type=media_type)


@app.post("/tts")
async def tts(
    body: TtsIn,
    make_source: Callable[[str | None], AudioSource] = Depends(get_source_factory),
    user: User | None = Depends(current_user_optional),
    db: Session = Depends(get_db),
    x_guest_token: str | None = Header(default=None),
) -> Response:
    """Render approved script text to audio via the configured AudioSource.

    Generation is gated (FR-A2/FR-A5): authenticated users go through has_access + the credit
    counter (free, non-blocking at launch); guests present a server-issued X-Guest-Token (from
    POST /auth/guest) good for GUEST_FREE_GENERATIONS, then must create an account. The guest
    allowance is reserved atomically BEFORE the billable synth (so concurrent requests can't both
    slip through) and released if the render fails (so a failure never burns the free generation).
    """
    # Hard char cap enforced BEFORE any (billable) outbound call.
    if len(body.text) > settings.max_script_chars:
        raise HTTPException(status_code=422, detail="text exceeds max_script_chars")

    # Strip PII before the text leaves us for the voice service (AC3: stripped from LLM/TTS calls).
    text = strip_pii(body.text)

    # Defense in depth (FR-G5): /script is the primary moderation gate (with theme context), but a
    # client could POST harmful text straight to /tts. Re-check the finalized text before any billable
    # synth. No theme context here, so this fails closed — a bare med name is blocked too.
    try:
        moderate(text)
    except ScriptModerationError as exc:
        raise HTTPException(
            status_code=422, detail={"message": exc.message, "blocked": exc.category}
        )

    # Resolve the chosen persona to a voice (US-005); reject an unknown one before any gating/charge.
    voice_id: str | None = None
    if body.persona_id is not None:
        voice_id = resolve_voice_id(body.persona_id)
        if voice_id is None:
            raise HTTPException(status_code=422, detail="unknown voice persona")
    # Build the source before the gate so a config error (missing key) is a clear 503, as before.
    source = make_source(voice_id)

    guest_id: uuid.UUID | None = None
    if user is not None:
        if not has_access(db, user.id, "generation"):
            raise HTTPException(status_code=403, detail="generation not available on your plan")
    else:
        if not x_guest_token:
            raise HTTPException(
                status_code=401,
                detail="sign in, or call POST /auth/guest for a free generation",
                headers={"WWW-Authenticate": "Bearer"},
            )
        try:
            guest_id = decode_guest_token(x_guest_token)
        except jwt.InvalidTokenError as exc:
            raise HTTPException(status_code=401, detail="invalid guest token") from exc
        if not reserve_guest_generation(db, guest_id):
            # Over-limit attempts don't bump the counter, so nothing to persist here.
            raise HTTPException(
                status_code=401, detail="free generation used — create an account to continue"
            )
        db.commit()  # commit the reservation before the (slow, billable) synth

    try:
        audio = await _synthesize(source, text)
    except HTTPException:
        if guest_id is not None:
            release_guest_generation(db, guest_id)  # render failed → don't burn the free credit
            db.commit()
        raise

    # Authed credit counts successful generations only (free/non-blocking at launch).
    if user is not None:
        record_generation(db, user.id)
        db.commit()

    return Response(content=audio, media_type=source.media_type)


async def _synthesize(source: AudioSource, text: str) -> bytes:
    try:
        return await source.synthesize(text)
    except AudioSourceError as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail={"message": exc.message, "retryable": exc.retryable},
        ) from exc
