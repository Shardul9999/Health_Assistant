"""Application settings, loaded from backend/.env via Pydantic Settings.

Every value here is either a local-infra default (safe to hardcode, points at
docker-compose) or a secret that MUST come from the environment. Nothing in this
file may contain a real credential.
"""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # --- local infra (matches docker-compose.yml; no accounts needed) ---
    database_url: str = "postgresql+asyncpg://health:localdevpassword@localhost:5432/health_assistant"
    redis_url: str = "redis://localhost:6379/0"

    # --- hosted services (accounts required) ---
    clerk_secret_key: str = ""
    clerk_jwks_url: str = ""
    groq_api_key: str = ""
    gemini_api_key: str = ""

    # --- tunables ---
    rate_limit_requests: int = 10
    rate_limit_window_s: int = 60
    similarity_threshold: float = 0.65
    retrieval_top_k: int = 5
    allowed_origins: str = "http://localhost:5173"

    # --- logging / environment ---
    environment: str = "development"  # "production" switches logs to JSON
    log_level: str = "INFO"

    @property
    def json_logs(self) -> bool:
        return self.environment.lower() == "production"

    # --- models ---
    # gemini-embedding-001 replaces the retired text-embedding-004. It defaults to
    # 3072 dims but supports Matryoshka truncation; we ask for 768 to keep the
    # schema (vector(768)) and the HNSW index unchanged.
    embedding_model: str = "gemini-embedding-001"
    embedding_dimensions: int = 768
    # Groq no longer serves llama-3.3-70b-versatile. gpt-oss-120b is the closest
    # current equivalent on the platform: 120B, 131k context, streams cleanly.
    groq_model: str = "openai/gpt-oss-120b"
    gemini_model: str = "gemini-2.5-flash"

    @property
    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.allowed_origins.split(",") if o.strip()]

    @property
    def alembic_url(self) -> str:
        """Alembic runs against the same DB; the async driver works there too."""
        return self.database_url


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
