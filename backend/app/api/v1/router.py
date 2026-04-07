"""API v1 — aggregated router."""

from fastapi import APIRouter

from app.api.v1.articles import router as articles_router
from app.api.v1.categories import router as categories_router
from app.api.v1.health import router as health_router
from app.api.v1.methodology import router as methodology_router
from app.api.v1.scrape import router as scrape_router
from app.api.v1.stats import router as stats_router
from app.api.v1.stories import router as stories_router

api_v1_router = APIRouter(prefix="/api/v1")

api_v1_router.include_router(health_router, tags=["Health"])
api_v1_router.include_router(articles_router, tags=["Articles"])
api_v1_router.include_router(stories_router, tags=["Stories"])
api_v1_router.include_router(categories_router, tags=["Categories"])
api_v1_router.include_router(stats_router, tags=["Dashboard"])
api_v1_router.include_router(methodology_router, tags=["Methodology"])
api_v1_router.include_router(scrape_router, tags=["Scraper"])
