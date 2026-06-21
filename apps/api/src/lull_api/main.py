from __future__ import annotations

import uuid

from fastapi import Depends, FastAPI, Header, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.orm import Session

from .audio import AudioSource, AudioSourceError, get_audio_source
from .auth import current_user_optional, router as auth_router
from .config import settings
from .db import get_db
from .entitlements import consume_guest_generation, has_access, record_generation
from .models import User
from .scripts import TrackSpec, build_script

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


class ScriptOut(BaseModel):
    script: str
    char_count: int
    est_seconds: float
    est_cost_usd: float
    components: dict[str, str]  # resolved choices (reveals 'ai' picks — FR-B3)


class TtsIn(BaseModel):
    text: str


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "audio_source": settings.audio_source}


@app.post("/script", response_model=ScriptOut)
def generate_script(spec_in: TrackSpecIn) -> ScriptOut:
    """Script first, audio later (FR-G1): returns text to preview + a cost/time estimate."""
    try:
        script, components = build_script(TrackSpec(**spec_in.model_dump()))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

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


def get_source() -> AudioSource:
    """Resolve the configured AudioSource; surface config errors as a clear 503."""
    try:
        return get_audio_source(settings)
    except RuntimeError as exc:
        raise HTTPException(
            status_code=503, detail={"message": str(exc), "retryable": False}
        ) from exc


@app.post("/tts")
async def tts(
    body: TtsIn,
    source: AudioSource = Depends(get_source),
    user: User | None = Depends(current_user_optional),
    db: Session = Depends(get_db),
    x_guest_id: str | None = Header(default=None),
) -> Response:
    """Render approved script text to audio via the configured AudioSource.

    Generation is gated (FR-A2/FR-A5): authenticated users go through has_access + the credit
    counter (free, non-blocking at launch); guests get GUEST_FREE_GENERATIONS via X-Guest-Id,
    then must create an account. Gating runs BEFORE the billable synth call.
    """
    # Hard char cap enforced BEFORE any (billable) outbound call.
    if len(body.text) > settings.max_script_chars:
        raise HTTPException(status_code=422, detail="text exceeds max_script_chars")

    if user is not None:
        if not has_access(db, user.id, "generation"):
            raise HTTPException(status_code=403, detail="generation not available on your plan")
        record_generation(db, user.id)
        db.commit()
    else:
        if not x_guest_id:
            raise HTTPException(
                status_code=401,
                detail="sign in, or send X-Guest-Id to use your free generation",
                headers={"WWW-Authenticate": "Bearer"},
            )
        try:
            guest_uuid = uuid.UUID(x_guest_id)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail="invalid X-Guest-Id") from exc
        if not consume_guest_generation(db, guest_uuid):
            db.commit()  # persist the (over-limit) attempt count
            raise HTTPException(
                status_code=401, detail="free generation used — create an account to continue"
            )
        db.commit()

    try:
        audio = await source.synthesize(body.text)
    except AudioSourceError as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail={"message": exc.message, "retryable": exc.retryable},
        ) from exc
    return Response(content=audio, media_type=source.media_type)
