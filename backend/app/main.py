"""IndiaGround — FastAPI application factory."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from app.api.v1.router import api_v1_router
from app.core import get_settings
from app.core.logging import logger


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    logger.info("🚀 IndiaGround API starting up")
    settings = get_settings()
    logger.info(f"Environment: {settings.APP_ENV}")
    logger.info(f"ML device: {settings.resolved_device}")
    yield
    logger.info("🛑 IndiaGround API shutting down")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()

    app = FastAPI(
        title="IndiaGround API",
        description=(
            "Automated News Bias & Fact-Check Platform for India. "
            "Scrapes Indian news, analyses each article for media bias "
            "and factual claim credibility, and presents a scored result."
        ),
        version="0.1.0",
        docs_url="/api/docs" if settings.DEBUG else None,
        redoc_url="/api/redoc" if settings.DEBUG else None,
        openapi_url="/api/openapi.json" if settings.DEBUG else None,
        lifespan=lifespan,
    )

    # ── Rate limiting ─────────────────────────────
    limiter = Limiter(key_func=get_remote_address)
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    # ── CORS ──────────────────────────────────────
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Routes ────────────────────────────────────
    app.include_router(api_v1_router)

    @app.get("/", include_in_schema=False)
    async def root():
        return {
            "service": "IndiaGround API",
            "version": "0.1.0",
            "docs": "/api/docs",
        }

    return app


app = create_app()
