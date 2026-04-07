"""RSS feed aggregator for Indian news sources.

Fully free, no API keys required.  Parses RSS/Atom feeds from:
  1. Google News India (category-specific)
  2. Direct feeds from major Indian outlets

Uses feedparser for robust RSS/Atom parsing and trafilatura for
full-text extraction when RSS only provides summaries.
"""

from __future__ import annotations

import asyncio
import re
from datetime import UTC, datetime
from typing import Any

import httpx

from app.core.logging import logger
from app.utils.hashing import compute_content_hash

# ── Google News RSS feeds (India, English) ────────

GOOGLE_NEWS_FEEDS: dict[str, str] = {
    "national": "https://news.google.com/rss/topics/CAAqIQgKIhtDQkFTRGdvSUwyMHZNRFZxYUdjU0FtVnVLQUFQAQ?hl=en-IN&gl=IN&ceid=IN:en",
    "business": "https://news.google.com/rss/topics/CAAqJggKIiBDQkFTRWdvSUwyMHZNRGx6TVdZU0FtVnVHZ0pKVGlnQVAB?hl=en-IN&gl=IN&ceid=IN:en",
    "technology": "https://news.google.com/rss/topics/CAAqJggKIiBDQkFTRWdvSUwyMHZNRGRqTVhZU0FtVnVHZ0pKVGlnQVAB?hl=en-IN&gl=IN&ceid=IN:en",
    "sports": "https://news.google.com/rss/topics/CAAqJggKIiBDQkFTRWdvSUwyMHZNRFp1ZEdvU0FtVnVHZ0pKVGlnQVAB?hl=en-IN&gl=IN&ceid=IN:en",
    "entertainment": "https://news.google.com/rss/topics/CAAqJggKIiBDQkFTRWdvSUwyMHZNREpxYW5RU0FtVnVHZ0pKVGlnQVAB?hl=en-IN&gl=IN&ceid=IN:en",
    "science": "https://news.google.com/rss/topics/CAAqJggKIiBDQkFTRWdvSUwyMHZNRFp0Y1RjU0FtVnVHZ0pKVGlnQVAB?hl=en-IN&gl=IN&ceid=IN:en",
    "world": "https://news.google.com/rss/topics/CAAqJggKIiBDQkFTRWdvSUwyMHZNRGx1YlY4U0FtVnVHZ0pKVGlnQVAB?hl=en-IN&gl=IN&ceid=IN:en",
}

# ── Direct RSS feeds from Indian outlets ──────────

DIRECT_FEEDS: dict[str, dict[str, str]] = {
    "The Hindu": {
        "url": "https://www.thehindu.com/news/national/feeder/default.rss",
        "category": "national",
    },
    "The Hindu - Business": {
        "url": "https://www.thehindu.com/business/feeder/default.rss",
        "category": "business",
    },
    "Indian Express": {
        "url": "https://indianexpress.com/section/india/feed/",
        "category": "national",
    },
    "Indian Express - Business": {
        "url": "https://indianexpress.com/section/business/feed/",
        "category": "business",
    },
    "NDTV - Latest": {
        "url": "https://feeds.feedburner.com/ndtvnews-latest",
        "category": "national",
    },
    "Hindustan Times": {
        "url": "https://www.hindustantimes.com/feeds/rss/india-news/rssfeed.xml",
        "category": "national",
    },
    "The Print": {
        "url": "https://theprint.in/feed/",
        "category": "national",
    },
    "Scroll.in": {
        "url": "https://scroll.in/rss/feed",
        "category": "national",
    },
    "Livemint": {
        "url": "https://www.livemint.com/rss/news",
        "category": "business",
    },
    "Business Standard": {
        "url": "https://www.business-standard.com/rss/home_page_top_stories.rss",
        "category": "business",
    },
    "Deccan Herald": {
        "url": "https://www.deccanherald.com/rss/india.rss",
        "category": "national",
    },
    "Times of India": {
        "url": "https://timesofindia.indiatimes.com/rssfeedstopstories.cms",
        "category": "national",
    },
    "India Today": {
        "url": "https://www.indiatoday.in/rss/home",
        "category": "national",
    },
    "The Wire": {
        "url": "https://thewire.in/feed",
        "category": "national",
    },
    "News18": {
        "url": "https://www.news18.com/rss/india.xml",
        "category": "national",
    },
}

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
}


def _parse_feed(feed_content: str) -> list[dict[str, Any]]:
    """Parse RSS/Atom feed content using feedparser."""
    try:
        import feedparser

        feed = feedparser.parse(feed_content)
        return feed.entries
    except Exception as e:
        logger.warning(f"feedparser failed: {e}")
        return []


def _clean_html(text: str) -> str:
    """Strip HTML tags from RSS content."""
    if not text:
        return ""
    clean = re.sub(r"<[^>]+>", "", text)
    clean = re.sub(r"\s+", " ", clean).strip()
    return clean


def _extract_source_from_google_news(title: str) -> tuple[str, str]:
    """Google News titles end with ' - Source Name'. Split them."""
    parts = title.rsplit(" - ", 1)
    if len(parts) == 2:
        return parts[0].strip(), parts[1].strip()
    return title, "Unknown"


def _parse_date(entry: dict) -> datetime | None:
    """Extract publish date from a feed entry."""
    for field in ("published_parsed", "updated_parsed"):
        time_struct = entry.get(field)
        if time_struct:
            try:
                from calendar import timegm

                return datetime.fromtimestamp(timegm(time_struct), tz=UTC)
            except (ValueError, OSError):
                continue
    return None


def _entry_to_article(
    entry: dict,
    category: str,
    source_override: str | None = None,
) -> dict[str, Any] | None:
    """Convert a feedparser entry to our article schema."""
    raw_title = entry.get("title", "").strip()
    if not raw_title:
        return None

    if source_override:
        title = raw_title
        source_name = source_override
    else:
        title, source_name = _extract_source_from_google_news(raw_title)

    summary = _clean_html(entry.get("summary", "") or entry.get("description", ""))[:500]
    if not summary:
        summary = title

    source_url = entry.get("link", "") or None
    published_at = _parse_date(entry)

    # Extract image from media content or enclosures
    image_url = None
    if entry.get("media_content"):
        image_url = entry["media_content"][0].get("url")
    elif entry.get("enclosures"):
        for enc in entry["enclosures"]:
            if "image" in enc.get("type", ""):
                image_url = enc.get("href") or enc.get("url")
                break

    content_hash = compute_content_hash(title, str(published_at))

    return {
        "title": title,
        "synopsis": summary,
        "author": entry.get("author"),
        "published_at": published_at,
        "category": category,
        "source_name": source_name,
        "source_url": source_url,
        "inshorts_url": None,
        "image_url": image_url,
        "content_hash": content_hash,
        "source_type": "rss",
        "status": "raw",
        "scraped_at": datetime.now(UTC),
    }


async def _fetch_feed(url: str) -> str:
    """Download RSS feed content."""
    try:
        async with httpx.AsyncClient(
            headers=_HEADERS, follow_redirects=True, timeout=20.0
        ) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            return resp.text
    except Exception as e:
        logger.warning(f"Failed to fetch RSS feed {url}: {e}")
        return ""


async def scrape_google_news_rss() -> list[dict[str, Any]]:
    """Fetch all Google News India category feeds."""
    all_articles: list[dict[str, Any]] = []

    for category, url in GOOGLE_NEWS_FEEDS.items():
        content = await _fetch_feed(url)
        if not content:
            continue

        entries = _parse_feed(content)
        for entry in entries[:20]:
            article = _entry_to_article(entry, category)
            if article:
                all_articles.append(article)

        await asyncio.sleep(0.3)

    logger.info(f"Google News RSS: fetched {len(all_articles)} articles")
    return all_articles


async def scrape_direct_feeds() -> list[dict[str, Any]]:
    """Fetch RSS feeds directly from Indian news outlets."""
    all_articles: list[dict[str, Any]] = []

    for source_label, feed_info in DIRECT_FEEDS.items():
        content = await _fetch_feed(feed_info["url"])
        if not content:
            continue

        entries = _parse_feed(content)
        source_name = source_label.split(" - ")[0]

        for entry in entries[:15]:
            article = _entry_to_article(
                entry,
                feed_info["category"],
                source_override=source_name,
            )
            if article:
                all_articles.append(article)

        await asyncio.sleep(0.2)

    logger.info(f"Direct RSS feeds: fetched {len(all_articles)} articles")
    return all_articles


async def scrape_all_rss() -> list[dict[str, Any]]:
    """Run both Google News RSS and direct outlet feeds."""
    google_articles = await scrape_google_news_rss()
    direct_articles = await scrape_direct_feeds()

    all_articles = google_articles + direct_articles
    logger.info(f"Total RSS: {len(all_articles)} articles from all feeds")
    return all_articles
