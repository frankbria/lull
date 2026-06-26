from __future__ import annotations

import asyncio
import os
import time
import uuid
from pathlib import Path
from typing import Callable

import jwt
from fastapi import Depends, FastAPI, Header, HTTPException, Request, Response
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
from .persistence import persist_track, script_checksum, store_audio
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
    # US-008: when an authenticated client sends the originating spec (+ resolved components), the
    # render is persisted as an account-scoped Track with metadata. Optional, so guests and legacy
    # callers still just get audio back.
    spec: TrackSpecIn | None = None
    components: dict[str, str] | None = None


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


# Per-IP fixed-window rate limit for the billable /script path (issue #48). Stub mode is free and
# stays ungated; in claude mode each call is a billable Anthropic request, so an unauthenticated
# caller must not be able to hammer it. ip -> (window_start_monotonic, count_in_window).
# ponytail: in-process fixed window — single-instance only; a shared store (Redis) is the
# multi-instance upgrade. Behind a reverse proxy, request.client.host is the proxy IP unless XFF is
# honored, so this degrades to a single global cap — per-client at the edge is the deploy concern.
_script_rate: dict[str, tuple[float, int]] = {}
_SCRIPT_RATE_WINDOW_S = 60.0
# Drop expired buckets once the map gets large, so an IP-rotating bot can't leak one entry per
# address for the process lifetime. The sweep is O(n) but runs only past this size, so steady-state
# cost stays low and memory is bounded by IPs actually seen within a window.
_SCRIPT_RATE_SWEEP_AT = 1024


def _script_rate_retry_after(ip: str, limit: int) -> float | None:
    """Record a call from `ip`; return None if it's within `limit` for the current window, else the
    seconds to wait before the window resets. Fixed window: the count resets on the first call after
    the window elapses."""
    now = time.monotonic()
    if len(_script_rate) >= _SCRIPT_RATE_SWEEP_AT:
        for stale in [k for k, (s, _) in _script_rate.items() if now - s >= _SCRIPT_RATE_WINDOW_S]:
            del _script_rate[stale]
    start, count = _script_rate.get(ip, (now, 0))
    if now - start >= _SCRIPT_RATE_WINDOW_S:
        start, count = now, 0
    count += 1
    _script_rate[ip] = (start, count)
    if count <= limit:
        return None
    return _SCRIPT_RATE_WINDOW_S - (now - start)


@app.post("/script", response_model=ScriptOut)
async def generate_script(
    spec_in: TrackSpecIn,
    request: Request,
    source: ScriptSource = Depends(get_script_source),
) -> ScriptOut:
    """Script first, audio later (FR-G1): returns text to preview + a cost/time estimate.

    Pipeline (PRD §): resolve AI picks -> generate -> moderate BEFORE TTS (FR-G5). A moderation block
    returns a safe 422 so prohibited content is never voiced.
    """
    # Cost gate (issue #48): in claude mode every call is a billable Anthropic request, so rate-limit
    # per client IP BEFORE generating — an unauthenticated caller can't drive unbounded spend. Stub
    # mode is free, so it stays ungated (offline dev + the free-preview UX are unaffected).
    limit = settings.script_rate_limit_per_min
    if settings.script_source == "claude" and limit > 0:
        client_ip = request.client.host if request.client else "unknown"
        retry_after = _script_rate_retry_after(client_ip, limit)
        if retry_after is not None:
            raise HTTPException(
                status_code=429,
                detail={
                    "message": "too many script requests — please slow down",
                    "retryable": True,
                },
                headers={"Retry-After": str(int(retry_after) + 1)},
            )

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
    # Dedup key over the exact (text, voice, source): an identical earlier render is served from disk
    # below instead of re-billing TTS (US-008 AC3). The source is part of the key so a stub WAV never
    # gets served in place of real ElevenLabs output after a config change.
    ext = _ext_for_media_type(source.media_type)
    # Key on the EFFECTIVE render voice, not the raw persona: the non-persona path renders with the
    # configured default voice (settings.elevenlabs_voice_id, mirrored from get_audio_source), so the
    # key must change if that default changes — otherwise a config swap serves audio in the old voice.
    effective_voice = voice_id if voice_id is not None else settings.elevenlabs_voice_id
    checksum = script_checksum(text, effective_voice, settings.audio_source)
    cache_path = Path(settings.audio_store_dir).resolve() / f"{checksum}.{ext}"

    # If this render will be persisted (authed + spec), resolve + validate the component metadata
    # server-side BEFORE any billable synth: a bad spec option, or client components that contradict
    # the spec, is a clean 422 (never a 500 after we've paid for TTS). The stored map is the canonical
    # server resolution (what /script returns), never a client-supplied or guessed value.
    persisted_components: dict[str, str] | None = None
    if user is not None and body.spec is not None:
        try:
            persisted_components = resolve_components(TrackSpec(**body.spec.model_dump()))
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        if body.components is not None and body.components != persisted_components:
            raise HTTPException(status_code=422, detail="components do not match spec")

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

    # The gate above is per generation request: a guest's one free generation is consumed even on a
    # cache hit below (they still get a rendered track). The cache saves *our* TTS spend, not the
    # user's allowance — and charging it closes a free-replay loophole.
    #
    # The reservation is already committed, so EVERY failure from here on must refund the guest's
    # free generation — a request that returns no audio must never burn the one free credit. One
    # guard around the whole render/persist/commit path covers cache read, synth, store, persist,
    # and the credit commit uniformly (it's a no-op for authenticated users, who hold no reservation).
    try:
        # The cache is the content-addressed file on disk (global, so it spares TTS spend for
        # everyone including guests — not only persisted authed tracks).
        audio: bytes | None = None
        audio_path: str
        if cache_path.exists():
            try:
                audio = cache_path.read_bytes()
                audio_path = str(cache_path)
                # Mark recently-used so the LRU eviction sweep (issue #51) keeps hot renders and
                # drops cold ones. Best-effort: a failed touch must not fail the request.
                try:
                    os.utime(cache_path, None)
                except OSError:
                    pass
            except OSError:
                audio = None  # unreadable cache file → treat as a miss and re-synthesize below
        if audio is None:
            audio = await _render_single_flight(checksum, source, text, ext)
            audio_path = str(cache_path)

        # Persist an account-scoped track with its metadata (US-008 AC1/AC2). Authed only: a guest
        # has no user row. Needs the originating spec; without it the call is a bare render.
        if user is not None and body.spec is not None:
            persist_track(
                db,
                user_id=user.id,
                spec=body.spec.model_dump(),
                components=persisted_components,  # server-resolved + validated above
                persona_id=body.persona_id,
                audio_path=audio_path,
                checksum=checksum,
                duration_seconds=len(text) / 12.5,  # ~150 wpm pacing; matches /script est_seconds
                source=settings.audio_source,
            )

        # Authed credit counts successful generations only (free/non-blocking at launch).
        if user is not None:
            record_generation(db, user.id)
            db.commit()
    except HTTPException:
        _release_guest_on_failure(
            db, guest_id
        )  # e.g. a mapped synth error — refund, keep its status
        raise
    except OSError as exc:
        _release_guest_on_failure(db, guest_id)
        raise HTTPException(
            status_code=503,
            detail={
                "message": "could not complete generation — please try again",
                "retryable": True,
            },
        ) from exc
    except asyncio.CancelledError:
        # A client disconnect mid-render cancels this request. CancelledError is a BaseException, so
        # `except Exception` below would miss it — refund explicitly so a disconnect never burns the
        # free generation. The shared single-flight render is shielded, so it survives for others.
        _release_guest_on_failure(db, guest_id)
        raise
    except Exception:
        _release_guest_on_failure(
            db, guest_id
        )  # refund, but surface the real error (don't mask it)
        raise

    return Response(content=audio, media_type=source.media_type)


def _release_guest_on_failure(db: Session, guest_id: uuid.UUID | None) -> None:
    """Give back a guest's reserved free generation when the render/store failed, so a request that
    returns no audio never burns the one free credit. No-op for authenticated users."""
    if guest_id is not None:
        release_guest_generation(db, guest_id)
        db.commit()


# Single-flight the synth-on-miss so concurrent identical renders don't each fire a billable TTS
# call: the first stores the in-flight task under its checksum, overlapping requests await the same
# one, and the file is written exactly once (mirrors _preview_cache). ponytail: in-process, so it
# collapses duplicates within one worker — the right scope for the single-instance deploy; a
# cross-process render reservation (e.g. a Postgres advisory lock) is the multi-instance upgrade.
_render_inflight: dict[str, asyncio.Task[bytes]] = {}


async def _render_single_flight(checksum: str, source: AudioSource, text: str, ext: str) -> bytes:
    task = _render_inflight.get(checksum)
    if task is None:

        async def render() -> bytes:
            audio = await _synthesize(source, text)
            store_audio(
                audio, checksum, ext, settings.audio_store_dir, settings.audio_store_max_bytes
            )
            return audio

        task = asyncio.ensure_future(render())
        # Evict on every exit (success, error, cancel) so a failed render never sticks as a poisoned
        # entry — the next request retries from scratch.
        task.add_done_callback(lambda t: _render_inflight.pop(checksum, None))
        _render_inflight[checksum] = task

    # shield: a client disconnect cancelling THIS request must not cancel the shared render others
    # are awaiting.
    return await asyncio.shield(task)


async def _synthesize(source: AudioSource, text: str) -> bytes:
    try:
        return await source.synthesize(text)
    except AudioSourceError as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail={"message": exc.message, "retryable": exc.retryable},
        ) from exc


def _ext_for_media_type(media_type: str) -> str:
    return "wav" if "wav" in media_type else "mp3"
