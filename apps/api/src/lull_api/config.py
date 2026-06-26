from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Public repo default — fine for local dev, MUST never sign tokens in a deployed environment.
_DEFAULT_JWT_SECRET = "dev-insecure-change-me-with-a-real-32B+-secret"
_DEV_ENVIRONMENTS = {"development", "dev", "local", "test"}
# HS256 security rests entirely on this secret, so a deployed one needs real entropy.
_MIN_JWT_SECRET_LEN = 32


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="LULL_", env_file=".env", extra="ignore")

    # Deployment environment. Anything outside _DEV_ENVIRONMENTS must supply a real LULL_JWT_SECRET.
    environment: str = "development"

    # "stub" plays/returns silent audio so the app runs offline with no API key.
    # "elevenlabs" requires elevenlabs_api_key.
    audio_source: str = "stub"

    # Postgres DSN. Local default matches docker-compose.yml; staging/prod override via
    # LULL_DATABASE_URL (Hostinger VPS Postgres).
    database_url: str = "postgresql+psycopg://lull:lull@localhost:5432/lull"

    # Browser CORS allow-list. "*" is fine for local dev; set LULL_CORS_ORIGINS to the real
    # web origin(s) in staging/prod (JSON list, e.g. ["https://app.example.com"]).
    cors_origins: list[str] = ["*"]

    elevenlabs_api_key: str | None = None
    elevenlabs_voice_id: str = (
        "EXAVITQu4vr4xnSDxMaL"  # ElevenLabs "Sarah" default; swap per persona
    )

    # Script generation. "stub" assembles the deterministic seed-library template so the app runs
    # offline with no API key; "claude" calls Anthropic with the hardened prompt (issue #14).
    script_source: str = "stub"
    anthropic_api_key: str | None = None
    # Per-generation call — opus is the default; set LULL_ANTHROPIC_MODEL=claude-sonnet-4-6 for a
    # cheaper run if quality allows.
    anthropic_model: str = "claude-opus-4-8"

    # Hard cap (FR-G6). ~ one 90-min hypnosis script is well under this.
    max_script_chars: int = 60_000

    # Per-IP cost gate for /script in claude mode (issue #48): max billable calls per client IP per
    # minute. Stub mode is free and stays ungated. <=0 disables the gate (operator escape hatch).
    script_rate_limit_per_min: int = 10

    # Rough ElevenLabs cost estimate, USD per 1k characters (tune against real billing).
    cost_per_1k_chars_usd: float = 0.15

    # Where synthesized audio is written + dedup-cached on disk (US-008). Files are named
    # {checksum}.{ext}, so an identical (script, voice) render reuses one file instead of re-billing
    # TTS. ponytail: local FS now; object storage / CDN when multi-instance.
    audio_store_dir: str = "audio_store"

    # On-write LRU eviction quota for audio_store_dir (issue #51): when the store exceeds this many
    # bytes, the oldest (least-recently-used, by mtime) files are deleted until it's back under cap.
    # Default 1 GiB; <=0 disables eviction.
    audio_store_max_bytes: int = 1024**3

    # Session JWT (HS256). Dev default is fine locally; MUST be overridden in staging/prod via
    # LULL_JWT_SECRET. ponytail: a shared secret + expiry, not a key-rotation service.
    jwt_secret: str = _DEFAULT_JWT_SECRET
    jwt_expire_minutes: int = 60 * 24 * 30  # 30 days — mobile sessions are long-lived

    # Accepted audiences for provider id_token verification (the app's OAuth client ids).
    # JSON lists, e.g. LULL_GOOGLE_CLIENT_IDS=["123.apps.googleusercontent.com"].
    google_client_ids: list[str] = []
    apple_client_ids: list[str] = []

    @model_validator(mode="after")
    def _require_strong_jwt_secret_outside_dev(self) -> "Settings":
        # Fail fast in deployed envs: the public default — or any short secret — would let an
        # attacker forge user tokens (HS256 is only as strong as this key).
        if self.environment not in _DEV_ENVIRONMENTS:
            if self.jwt_secret == _DEFAULT_JWT_SECRET:
                raise ValueError(
                    f"LULL_JWT_SECRET must be set in environment '{self.environment}' "
                    "(refusing to sign tokens with the public default)"
                )
            if len(self.jwt_secret) < _MIN_JWT_SECRET_LEN:
                raise ValueError(
                    f"LULL_JWT_SECRET must be at least {_MIN_JWT_SECRET_LEN} characters "
                    f"in environment '{self.environment}'"
                )
        return self


settings = Settings()
