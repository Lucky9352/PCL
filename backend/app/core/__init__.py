"""IndiaGround — Pydantic Settings from .env."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

# Resolve .env: check backend dir first, then repo root
_backend_dir = Path(__file__).resolve().parent.parent.parent
_repo_root = _backend_dir.parent
_env_file = _backend_dir / ".env"
if not _env_file.exists():
    _env_file = _repo_root / ".env"


class Settings(BaseSettings):
    """Application configuration — all values loaded from environment / .env file."""

    model_config = SettingsConfigDict(
        env_file=str(_env_file),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ── App ───────────────────────────────────────
    APP_ENV: Literal["development", "production", "testing"] = "development"
    DEBUG: bool = True
    SECRET_KEY: str = "dev-insecure-key-min-50-chars-please-replace-xxxxxxxxxxxxxxxxxxxxx"

    # ── Database ──────────────────────────────────
    DATABASE_URL: str = "postgresql+asyncpg://indiaground:indiaground@localhost:5432/indiaground"
    DATABASE_URL_SYNC: str = "postgresql://indiaground:indiaground@localhost:5432/indiaground"

    # ── Redis / Celery ────────────────────────────
    REDIS_URL: str = "redis://127.0.0.1:6379/0"
    CELERY_BROKER_URL: str = "redis://127.0.0.1:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://127.0.0.1:6379/0"

    # ── CORS ──────────────────────────────────────
    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:3000"

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    # ── Search APIs ───────────────────────────────
    GOOGLE_FACTCHECK_API_KEY: str = ""
    NEWSAPI_KEY: str = ""

    # ── Scraper ───────────────────────────────────
    SCRAPE_INTERVAL_MINUTES: int = 30

    # ── ML Device ─────────────────────────────────
    ML_DEVICE: str = "auto"

    @property
    def resolved_device(self) -> str:
        """Detect best available compute device: CUDA > MPS > CPU."""
        if self.ML_DEVICE != "auto":
            return self.ML_DEVICE
        try:
            import torch

            if torch.cuda.is_available():
                return "cuda"
            if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
                return "mps"
        except ImportError:
            pass
        return "cpu"


@lru_cache
def get_settings() -> Settings:
    return Settings()
