"""Inshorts news scraper — JSON API-based."""

from __future__ import annotations

import asyncio
import contextlib
import json
import re
from datetime import UTC, datetime
from typing import Any

import httpx

from app.core.logging import logger
from app.utils.hashing import compute_content_hash

# Inshorts categories to scrape
CATEGORIES = [
    "national",
    "business",
    "sports",
    "world",
    "politics",
    "technology",
    "startup",
    "entertainment",
    "science",
    "automobile",
]

# Inshorts base URL
_API_BASE = "https://inshorts.com/en/read"
_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}


async def scrape_inshorts_category(category: str) -> list[dict[str, Any]]:
    """Scrape articles from a single Inshorts category via their JSON API.

    Args:
        category: The Inshorts category slug (e.g. 'national', 'sports').

    Returns:
        List of article dicts with scraped fields.
    """
    articles: list[dict[str, Any]] = []

    try:
        async with httpx.AsyncClient(
            headers=_HEADERS,
            follow_redirects=True,
            timeout=30.0,
        ) as client:
            url = f"{_API_BASE}/{category}"
            logger.info(f"Scraping Inshorts category: {category} — {url}")

            response = await client.get(url)
            response.raise_for_status()
            html = response.text

        match = re.search(r"window\.__STATE__\s*=\s*(\{.*?\});?</script>", html, re.DOTALL)
        if not match:
            logger.warning(f"Could not find window.__STATE__ for {category}")
            return []

        try:
            data = json.loads(match.group(1))
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON for {category}: {e}")
            return []

        news_list = data.get("news_list", {}).get("list", [])
        logger.info(f"Page returned {len(news_list)} articles for '{category}'")

        for item in news_list:
            try:
                article = _extract_article_from_api(item, category)
                if article:
                    articles.append(article)
            except Exception as e:
                logger.warning(f"Failed to extract API article: {e}")
                continue

    except Exception as e:
        logger.error(f"API scraping failed for {category}: {e}")

    logger.info(f"Scraped {len(articles)} articles from '{category}'")
    return articles


def _extract_article_from_api(item: dict[str, Any], category: str) -> dict[str, Any] | None:
    """Extract article data from an Inshorts API response item."""
    news = item.get("news_obj", {})
    if not news:
        return None

    title = news.get("title", "").strip()
    if not title:
        return None

    synopsis = news.get("content", "").strip()
    author = news.get("author_name", "").strip() or None
    source_name = news.get("source_name", "").strip() or None
    source_url = news.get("source_url") or None
    image_url = news.get("image_url") or None
    inshorts_url = news.get("shortened_url") or None

    # Parse timestamp — created_at is epoch milliseconds
    created_at_ms = news.get("created_at")
    published_at = None
    if created_at_ms:
        with contextlib.suppress(ValueError, OSError):
            published_at = datetime.fromtimestamp(created_at_ms / 1000, tz=UTC)

    # Use API categories if available, fallback to the requested category
    api_categories = news.get("category_names", [])
    article_category = api_categories[0] if api_categories else category

    content_hash = compute_content_hash(title, str(published_at))

    return {
        "title": title,
        "synopsis": synopsis,
        "author": author,
        "published_at": published_at,
        "category": article_category,
        "source_name": source_name,
        "source_url": source_url,
        "inshorts_url": inshorts_url,
        "image_url": image_url,
        "content_hash": content_hash,
        "status": "raw",
        "scraped_at": datetime.now(UTC),
    }


def _parse_datetime(value: str | None) -> datetime | None:
    """Best-effort parse of various datetime formats."""
    if not value:
        return None
    value = value.strip()

    # Try ISO format first
    for fmt in [
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%dT%H:%M:%S.%f%z",
        "%Y-%m-%d %H:%M:%S",
        "%B %d, %Y",
        "%b %d, %Y",
    ]:
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue

    # Try dateutil as fallback
    try:
        from dateutil import parser

        return parser.parse(value)
    except Exception:
        pass

    return None


async def scrape_all_categories() -> list[dict[str, Any]]:
    """Scrape all Inshorts categories and return all articles."""
    all_articles = []

    for category in CATEGORIES:
        try:
            articles = await scrape_inshorts_category(category)
            all_articles.extend(articles)
        except Exception as e:
            logger.error(f"Failed to scrape category '{category}': {e}")
            continue

        await asyncio.sleep(0.5)

    logger.info(f"Total scraped: {len(all_articles)} articles across {len(CATEGORIES)} categories")
    return all_articles
