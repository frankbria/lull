from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="LULL_", env_file=".env", extra="ignore")

    # "stub" plays/returns silent audio so the app runs offline with no API key.
    # "elevenlabs" requires elevenlabs_api_key.
    audio_source: str = "stub"
    elevenlabs_api_key: str | None = None
    elevenlabs_voice_id: str = "EXAVITQu4vr4xnSDxMaL"  # ElevenLabs "Sarah" default; swap per persona

    # Hard cap (FR-G6). ~ one 90-min hypnosis script is well under this.
    max_script_chars: int = 60_000

    # Rough ElevenLabs cost estimate, USD per 1k characters (tune against real billing).
    cost_per_1k_chars_usd: float = 0.15


settings = Settings()
