"""NewsAPI.org integration for multi-source Indian news ingestion.

Uses the free tier (100 requests/day, 24h delay on /everything).
  - /v2/top-headlines?country=in  → Latest headlines from Indian sources
  - /v2/everything?q=india        → Broader search (24h delayed on free tier)

Requires NEWSAPI_KEY in .env.  If not set, this module is a no-op.
"""

from __future__ import annotations

import asyncio
import contextlib
from datetime import UTC, datetime
from typing import Any

import httpx

from app.core import get_settings
from app.core.logging import logger
from app.utils.hashing import compute_content_hash

_BASE_URL = "https://newsapi.org/v2"

INDIA_CATEGORY_MAP = {
    "business": "business",
    "entertainment": "entertainment",
    "general": "national",
    "health": "science",
    "science": "science",
    "sports": "sports",
    "technology": "technology",
}


async def _fetch_newsapi(
    endpoint: str,
    params: dict[str, Any],
) -> list[dict[str, Any]]:
    """Generic NewsAPI HTTP call."""
    settings = get_settings()
    if not settings.NEWSAPI_KEY:
        return []

    params["apiKey"] = settings.NEWSAPI_KEY
    url = f"{_BASE_URL}/{endpoint}"

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()

        if data.get("status") != "ok":
            logger.warning(f"NewsAPI returned status: {data.get('status')}")
            return []

        return data.get("articles", [])
    except Exception as e:
        logger.error(f"NewsAPI fetch failed ({endpoint}): {e}")
        return []


def _normalize_article(raw: dict[str, Any], category: str) -> dict[str, Any] | None:
    """Convert a NewsAPI article to our internal schema."""
    title = (raw.get("title") or "").strip()
    if not title or title == "[Removed]":
        return None

    description = (raw.get("description") or "").strip()
    content = (raw.get("content") or "").strip()
    # NewsAPI free tier truncates content; prefer description for synopsis
    synopsis = description or content[:300] if content else ""
    if not synopsis:
        return None

    source = raw.get("source", {})
    source_name = (source.get("name") or "").strip() or None
    author = (raw.get("author") or "").strip() or None
    source_url = raw.get("url") or None
    image_url = raw.get("urlToImage") or None

    published_at = None
    if raw.get("publishedAt"):
        with contextlib.suppress(ValueError, AttributeError):
            published_at = datetime.fromisoformat(raw["publishedAt"].replace("Z", "+00:00"))

    content_hash = compute_content_hash(title, str(published_at))

    return {
        "title": title,
        "synopsis": synopsis,
        "author": author,
        "published_at": published_at,
        "category": category,
        "source_name": source_name,
        "source_url": source_url,
        "inshorts_url": None,
        "image_url": image_url,
        "content_hash": content_hash,
        "source_type": "newsapi",
        "status": "raw",
        "scraped_at": datetime.now(UTC),
    }


async def scrape_newsapi_headlines() -> list[dict[str, Any]]:
    """Fetch top headlines from India across all categories.

    Free tier: 100 requests/day total.  We use ~7 requests here
    (one per category).
    """
    settings = get_settings()
    if not settings.NEWSAPI_KEY:
        logger.info("NewsAPI key not set — skipping headline fetch")
        return []

    all_articles: list[dict[str, Any]] = []

    for api_cat, our_cat in INDIA_CATEGORY_MAP.items():
        raw_articles = await _fetch_newsapi(
            "top-headlines",
            {"country": "in", "category": api_cat, "pageSize": 20},
        )

        for raw in raw_articles:
            article = _normalize_article(raw, our_cat)
            if article:
                all_articles.append(article)

        await asyncio.sleep(0.3)

    logger.info(f"NewsAPI: fetched {len(all_articles)} headlines from India")
    return all_articles


async def scrape_newsapi_everything(query: str = "India") -> list[dict[str, Any]]:
    """Search NewsAPI /everything for broader India coverage.

    Note: Free tier has a 24-hour delay on this endpoint.
    """
    settings = get_settings()
    if not settings.NEWSAPI_KEY:
        return []

    raw_articles = await _fetch_newsapi(
        "everything",
        {
            "q": query,
            "language": "en",
            "sortBy": "publishedAt",
            "pageSize": 50,
        },
    )

    articles = []
    for raw in raw_articles:
        article = _normalize_article(raw, "national")
        if article:
            articles.append(article)

    logger.info(f"NewsAPI everything: fetched {len(articles)} articles for '{query}'")
    return articles
