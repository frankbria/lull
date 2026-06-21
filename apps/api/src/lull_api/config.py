from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Public repo default — fine for local dev, MUST never sign tokens in a deployed environment.
_DEFAULT_JWT_SECRET = "dev-insecure-change-me-with-a-real-32B+-secret"
_DEV_ENVIRONMENTS = {"development", "dev", "local", "test"}


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

    # Hard cap (FR-G6). ~ one 90-min hypnosis script is well under this.
    max_script_chars: int = 60_000

    # Rough ElevenLabs cost estimate, USD per 1k characters (tune against real billing).
    cost_per_1k_chars_usd: float = 0.15

    # Session JWT (HS256). Dev default is fine locally; MUST be overridden in staging/prod via
    # LULL_JWT_SECRET. ponytail: a shared secret + expiry, not a key-rotation service.
    jwt_secret: str = _DEFAULT_JWT_SECRET
    jwt_expire_minutes: int = 60 * 24 * 30  # 30 days — mobile sessions are long-lived

    # Accepted audiences for provider id_token verification (the app's OAuth client ids).
    # JSON lists, e.g. LULL_GOOGLE_CLIENT_IDS=["123.apps.googleusercontent.com"].
    google_client_ids: list[str] = []
    apple_client_ids: list[str] = []

    @model_validator(mode="after")
    def _require_real_jwt_secret_outside_dev(self) -> "Settings":
        # Fail fast: a deployed env using the public default secret would let anyone forge tokens.
        if self.environment not in _DEV_ENVIRONMENTS and self.jwt_secret == _DEFAULT_JWT_SECRET:
            raise ValueError(
                f"LULL_JWT_SECRET must be set in environment '{self.environment}' "
                "(refusing to sign tokens with the public default)"
            )
        return self


settings = Settings()
