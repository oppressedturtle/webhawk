"""Application configuration.

Settings are loaded from the environment (and an optional local ``.env``) and
validated once at import time, so the process fails fast with a clear error
instead of surfacing ``None`` deep inside a request handler later.
"""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Strongly-typed application settings."""

    model_config = SettingsConfigDict(
        env_prefix="WEBHAWK_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- Runtime ---
    environment: str = Field(
        default="development",
        description="One of: development | test | production.",
    )
    debug: bool = Field(default=False)

    # --- HTTP ---
    host: str = Field(default="0.0.0.0")
    port: int = Field(default=8000, ge=1, le=65535)

    # Allowed CORS origins for the React dashboard (comma-separated in env).
    cors_origins: list[str] = Field(default=["http://localhost:5173"])

    # --- Datastores (wired up in a later phase) ---
    database_url: str = Field(
        default="postgresql+psycopg://webhawk:webhawk@localhost:5432/webhawk",
        description="SQLAlchemy/psycopg connection URL.",
    )
    redis_url: str = Field(default="redis://localhost:6379/0")

    @property
    def is_production(self) -> bool:
        return self.environment == "production"


@lru_cache
def get_settings() -> Settings:
    """Return a cached :class:`Settings` instance (one parse per process)."""
    return Settings()
