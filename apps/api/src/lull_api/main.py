from __future__ import annotations

from fastapi import FastAPI, HTTPException, Response
from pydantic import BaseModel

from .audio import get_audio_source
from .config import settings
from .scripts import TrackSpec, build_script

app = FastAPI(title="Lull API", version="0.1.0")


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
        raise HTTPException(status_code=422, detail=f"script exceeds {settings.max_script_chars} chars")

    return ScriptOut(
        script=script,
        char_count=chars,
        est_seconds=chars / 12.5,  # ~150 wpm hypnosis pacing
        est_cost_usd=round(chars / 1000 * settings.cost_per_1k_chars_usd, 4),
        components=components,
    )


@app.post("/tts")
async def tts(body: TtsIn) -> Response:
    """Render approved script text to audio via the configured AudioSource."""
    if len(body.text) > settings.max_script_chars:
        raise HTTPException(status_code=422, detail="text exceeds max_script_chars")
    source = get_audio_source(settings)
    audio = await source.synthesize(body.text)
    return Response(content=audio, media_type=source.media_type)
