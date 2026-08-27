from __future__ import annotations

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: str = Field(default="development", alias="APP_ENV")
    app_host: str = Field(default="0.0.0.0", alias="APP_HOST")
    app_port: int = Field(default=8000, alias="APP_PORT")
    app_cors_origins: str = Field(default="http://localhost:3000", alias="APP_CORS_ORIGINS")
    max_request_size_bytes: int = Field(default=65536, alias="APP_MAX_REQUEST_SIZE_BYTES")
    max_message_chars: int = Field(default=4000, alias="APP_MAX_MESSAGE_CHARS")
    request_timeout_seconds: int = Field(default=60, alias="APP_REQUEST_TIMEOUT_SECONDS")

    model_backend: str = Field(default="litellm", alias="MODEL_BACKEND")
    default_model_alias: str = Field(default="fast", alias="DEFAULT_MODEL_ALIAS")
    model_config_path: Path = Field(default=Path("litellm.yaml"), alias="MODEL_CONFIG_PATH")
    model_timeout_seconds: int = Field(default=45, alias="MODEL_TIMEOUT_SECONDS")
    model_max_tokens: int = Field(default=4096, alias="MODEL_MAX_TOKENS", ge=1)
    model_catalog_timeout_seconds: int = Field(default=10, alias="MODEL_CATALOG_TIMEOUT_SECONDS", ge=1)
    dynamic_model_config_path: Path = Field(default=Path("data/models.json"), alias="DYNAMIC_MODEL_CONFIG_PATH")
    agent_config_path: Path = Field(default=Path("data/agents.json"), alias="AGENT_CONFIG_PATH")
    healthcheck_timeout_seconds: int = Field(default=3, alias="HEALTHCHECK_TIMEOUT_SECONDS")

    ollama_base_url: str = Field(default="http://localhost:11434", alias="OLLAMA_BASE_URL")
    openrouter_api_key: str | None = Field(default=None, alias="OPENROUTER_API_KEY")
    huggingface_api_key: str | None = Field(default=None, alias="HF_TOKEN")
    state_backend: str = Field(default="memory", alias="STATE_BACKEND")
    database_url_override: str | None = Field(default=None, alias="DATABASE_URL")
    postgres_host: str = Field(default="localhost", alias="POSTGRES_HOST")
    postgres_port: int = Field(default=5432, alias="POSTGRES_PORT")
    postgres_db: str = Field(default="agentic_ai_platform", alias="POSTGRES_DB")
    postgres_user: str = Field(default="postgres", alias="POSTGRES_USER")
    postgres_password: str = Field(default="postgres", alias="POSTGRES_PASSWORD")
    filesystem_mcp_allowed_root: Path = Field(default=Path("."), alias="FILESYSTEM_MCP_ALLOWED_ROOT")
    governance_config_path: Path = Field(default=Path("data/governance.json"), alias="GOVERNANCE_CONFIG_PATH")
    news_rss_feeds: str = Field(
        default="https://news.google.com/rss/search?q={query}&hl=pt-BR&gl=BR&ceid=BR:pt-419",
        alias="NEWS_RSS_FEEDS",
    )
    news_timeout_seconds: int = Field(default=8, alias="NEWS_TIMEOUT_SECONDS")
    news_max_items: int = Field(default=5, alias="NEWS_MAX_ITEMS")
    langfuse_enabled: bool = Field(default=False, alias="LANGFUSE_ENABLED")
    langfuse_public_key: str | None = Field(default=None, alias="LANGFUSE_PUBLIC_KEY")
    langfuse_secret_key: str | None = Field(default=None, alias="LANGFUSE_SECRET_KEY")
    langfuse_base_url: str = Field(default="http://localhost:3000", alias="LANGFUSE_BASE_URL")

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.app_cors_origins.split(",") if origin.strip()]

    @property
    def database_url(self) -> str:
        if self.database_url_override:
            return self.database_url_override
        return (
            f"postgresql+psycopg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )
