"""
Application configuration — loaded from environment variables via Pydantic Settings.
No secrets are hardcoded here.
"""

from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """All runtime configuration for Firomsa AI Secretary."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Server ────────────────────────────────────────────────────────────────
    port: int = Field(default=8000, description="Uvicorn listen port")
    debug: bool = Field(default=False, description="Enable hot-reload (dev only)")
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    cors_origins: list[str] = Field(
        default=["http://localhost:3000"],
        description="Allowed CORS origins",
    )

    # ── Security ──────────────────────────────────────────────────────────────
    secret_key: str = Field(
        ...,
        description="Random secret used for session signing and token generation",
    )

    # ── Database ──────────────────────────────────────────────────────────────
    database_url: str = Field(
        ...,
        description="Async PostgreSQL connection string, e.g. postgresql+asyncpg://user:pass@host/db",
    )

    # ── Telegram MTProto ──────────────────────────────────────────────────────
    telegram_api_id: int = Field(
        ...,
        description="API ID from https://my.telegram.org/apps",
    )
    telegram_api_hash: str = Field(
        ...,
        description="API hash from https://my.telegram.org/apps",
    )
    telegram_phone: str = Field(
        ...,
        description="Your Telegram phone number with country code, e.g. +1234567890",
    )
    telegram_session: str = Field(
        default="firomsa_session",
        description="Name of the Telethon session file (stored on disk or in DB)",
    )

    # ── AI Providers ──────────────────────────────────────────────────────────
    openai_api_key: str | None = Field(
        default=None,
        description="OpenAI API key — optional if using Groq",
    )
    openai_base_url: str = Field(
        default="https://api.openai.com/v1",
        description="OpenAI-compatible base URL (swap to point at any compatible provider)",
    )
    openai_model: str = Field(
        default="gpt-4o",
        description="Default OpenAI model identifier",
    )

    groq_api_key: str | None = Field(
        default=None,
        description="Groq API key — optional if using OpenAI",
    )
    groq_base_url: str = Field(
        default="https://api.groq.com/openai/v1",
        description="Groq OpenAI-compatible base URL",
    )
    groq_model: str = Field(
        default="llama-3.3-70b-versatile",
        description="Default Groq model identifier",
    )

    # Active AI provider: "openai" | "groq"
    ai_provider: Literal["openai", "groq"] = Field(
        default="openai",
        description="Which AI provider the agent will use",
    )

    @field_validator("database_url")
    @classmethod
    def ensure_async_driver(cls, v: str) -> str:
        """Guarantee the DB URL uses an async driver."""
        if v.startswith("postgresql://") or v.startswith("postgres://"):
            return v.replace("postgresql://", "postgresql+asyncpg://", 1).replace(
                "postgres://", "postgresql+asyncpg://", 1
            )
        return v


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings singleton (loaded once at startup)."""
    return Settings()  # type: ignore[call-arg]


# Module-level convenience alias
settings: Settings = get_settings()
