"""Central application configuration.

All values come from environment variables (12-factor). Secrets are never
hardcoded. Access via get_settings() — cached by lru_cache.
"""
from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# apps/api/app/core/config.py → parents[4] = repository root.
# Resolved absolutely so the .env is found regardless of CWD.
_REPO_ROOT = Path(__file__).resolve().parents[4]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=[str(_REPO_ROOT / ".env"), ".env"],  # root first, CWD override second
        env_file_encoding="utf-8",
        extra="ignore",
    )

    environment: str = "development"
    log_level: str = "INFO"

    # Supabase
    supabase_url: str = "https://your-project.supabase.co"
    supabase_anon_key: str = ""
    supabase_service_role_key: str = ""
    supabase_storage_bucket: str = "lattice-private"
    # Legacy projects sign JWTs with this shared secret instead of JWKS.
    supabase_jwt_secret: str | None = None
    # Comma-separated addresses allowed to use the production app.
    allowed_emails: str = ""
    database_url: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/postgres",
        description="Async SQLAlchemy URL (asyncpg driver)",
    )

    # AI providers
    google_api_key: str | None = None
    # Verified working with response_schema structured output.
    gemini_model: str = "gemini-2.5-flash"
    # Verified 768-dim output (matches pgvector columns).
    gemini_embedding_model: str = "gemini-embedding-001"

    # Search / discovery
    tavily_api_key: str | None = None

    # OpenRouter (free LLM tier; takes priority over Gemini for text gen)
    openrouter_api_key: str | None = None
    openrouter_model: str | None = None
    ranking_openrouter_models: str = ""

    # CORS
    web_origin: str = "http://localhost:3000"

    @property
    def is_production(self) -> bool:
        return self.environment == "production"

    @property
    def jwks_url(self) -> str:
        return f"{self.supabase_url}/auth/v1/.well-known/jwks.json"

    @property
    def allowed_email_set(self) -> set[str]:
        return {email.strip().casefold() for email in self.allowed_emails.split(",") if email.strip()}


@lru_cache
def get_settings() -> Settings:
    return Settings()
