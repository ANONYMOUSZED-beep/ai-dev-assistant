"""Application configuration.

All settings are environment-driven and validated at startup via pydantic-settings.
A single cached :func:`get_settings` instance is shared across the application.
"""

from __future__ import annotations

import json
from functools import lru_cache
from typing import Annotated, Literal

from pydantic import Field, computed_field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

VectorStoreName = Literal["faiss", "chroma", "pgvector"]
LLMProviderName = Literal["openai", "anthropic", "gemini", "deepseek", "qwen", "groq"]
Environment = Literal["development", "production"]


class Settings(BaseSettings):
    """Strongly-typed application settings loaded from environment / ``.env``."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        # Strip stray whitespace/newlines from env values — pasting secrets into
        # dashboards (e.g. Hugging Face) often appends a trailing "\n".
        str_strip_whitespace=True,
    )

    # ── Application ──────────────────────────────────────────────
    app_name: str = "AI Developer Assistant"
    environment: Environment = "development"
    log_level: str = "INFO"
    api_v1_prefix: str = "/api/v1"
    # Accepts a JSON list (["https://a", "https://b"]) OR a plain/comma-separated
    # string (https://a,https://b) — see the validator below.
    backend_cors_origins: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: ["http://localhost:3000"]
    )
    # Optional regex matching allowed origins, in addition to the explicit list above.
    # Useful for platforms with rotating preview URLs (e.g. Vercel), so you don't have
    # to enumerate every deployment domain. Example: r"https://.*\.vercel\.app"
    backend_cors_origin_regex: str | None = None

    # ── Security ─────────────────────────────────────────────────
    # Allowed client API keys. When empty, authentication is disabled (local dev).
    # Accepts JSON list or comma-separated string, like backend_cors_origins.
    api_keys: Annotated[list[str], NoDecode] = Field(default_factory=list)

    @field_validator("backend_cors_origins", "api_keys", mode="before")
    @classmethod
    def _parse_str_list(cls, value: object) -> object:
        """Parse env values that may be JSON lists, comma-separated, or a single item.

        Env vars can't hold Python lists, and requiring strict JSON is a common
        deployment foot-gun. This accepts all of: '["a","b"]', 'a,b', and 'a'.
        """
        if not isinstance(value, str):
            return value
        text = value.strip()
        if not text:
            return []
        if text.startswith("["):
            try:
                return json.loads(text)
            except json.JSONDecodeError:
                pass  # fall through to comma-splitting
        return [item.strip() for item in text.split(",") if item.strip()]
    # Fixed-window request cap per client, per minute. 0 disables rate limiting.
    rate_limit_per_minute: int = 60

    # ── Auth (JWT) ───────────────────────────────────────────────
    # Secret used to sign JWTs. MUST be set to a long random value in production.
    jwt_secret: str = "dev-insecure-change-me"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24 * 7  # 7 days
    # Google OAuth 2.0 Web client id used to verify "Sign in with Google" ID tokens.
    # When unset, the Google sign-in endpoint returns an error and the frontend hides
    # the button, so username/password auth keeps working unchanged.
    google_client_id: str | None = None

    # ── Database ─────────────────────────────────────────────────
    postgres_user: str = "devassist"
    postgres_password: str = "devassist"
    postgres_db: str = "devassist"
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    database_url: str | None = None

    # ── Redis ────────────────────────────────────────────────────
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0

    # ── RAG / embeddings ─────────────────────────────────────────
    embedding_model: str = "BAAI/bge-m3"
    reranker_model: str = "BAAI/bge-reranker-v2-m3"
    vector_store: VectorStoreName = "faiss"
    vector_store_path: str = "./data/vectorstore"
    chunk_size: int = 800
    chunk_overlap: int = 120
    retrieval_top_k: int = 20
    rerank_top_k: int = 6

    # ── LLM ──────────────────────────────────────────────────────
    llm_provider: LLMProviderName = "openai"
    llm_model: str = "gpt-4o-mini"
    llm_temperature: float = 0.1
    llm_max_tokens: int = 2048

    openai_api_key: str | None = None
    anthropic_api_key: str | None = None
    google_api_key: str | None = None
    deepseek_api_key: str | None = None
    qwen_api_key: str | None = None
    groq_api_key: str | None = None

    # ── GitHub ───────────────────────────────────────────────────
    github_token: str | None = None

    @computed_field  # type: ignore[prop-decorator]
    @property
    def async_database_url(self) -> str:
        """Async SQLAlchemy connection string."""
        if self.database_url:
            return self.database_url
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def redis_url(self) -> str:
        """Redis connection string."""
        return f"redis://{self.redis_host}:{self.redis_port}/{self.redis_db}"

    @computed_field  # type: ignore[prop-decorator]
    @property
    def is_production(self) -> bool:
        return self.environment == "production"

    @computed_field  # type: ignore[prop-decorator]
    @property
    def auth_enabled(self) -> bool:
        """True when at least one API key is configured."""
        return bool(self.api_keys)


@lru_cache
def get_settings() -> Settings:
    """Return the cached application settings singleton."""
    return Settings()
