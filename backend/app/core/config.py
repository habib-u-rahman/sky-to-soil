"""Application settings, loaded from environment / .env."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
APP_DIR = BACKEND_DIR / "app"
CACHE_DIR = BACKEND_DIR / "cache"
DATA_DIR = APP_DIR / "data"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=str(BACKEND_DIR / ".env"), extra="ignore")

    groq_api_key: str = ""
    extra_cors_origins: str = ""
    s2s_debug: bool = False

    # NASA POWER date range: 2001-01-01 through the latest full calendar year.
    power_start_year: int = 2001

    # HTTP client behaviour for all upstream clients.
    http_timeout_seconds: float = 30.0
    http_max_retries: int = 3

    cache_ttl_seconds: int = 60 * 60 * 24 * 7  # 7 days

    @property
    def cors_origins(self) -> list[str]:
        origins = ["http://localhost:3000"]
        if self.extra_cors_origins:
            origins.extend(o.strip() for o in self.extra_cors_origins.split(",") if o.strip())
        return origins


@lru_cache
def get_settings() -> Settings:
    return Settings()
