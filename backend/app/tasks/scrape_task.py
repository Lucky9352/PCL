"""Celery tasks — multi-source news scraping.

Scrapes from three source types:
  1. Inshorts (JSON API) — primary, always runs
  2. RSS feeds (Google News + direct Indian outlets) — always runs, free
  3. NewsAPI (if NEWSAPI_KEY is set) — optional, free tier 100 req/day
"""

from __future__ import annotations

import asyncio

from sqlalchemy import select

from app.core.celery_app import celery_app
from app.core.logging import logger


def _get_sync_session():
    """Get a synchronous DB session for Celery tasks."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    from app.core import get_settings

    settings = get_settings()
    engine = create_engine(settings.DATABASE_URL_SYNC, pool_pre_ping=True)
    SessionLocal = sessionmaker(bind=engine)
    return SessionLocal()


def _insert_articles(session, articles_data: list[dict], source_label: str) -> tuple[int, int]:
    """Insert articles into DB with dedup. Returns (inserted, skipped)."""
    from app.db.models import Article

    inserted = 0
    skipped = 0

    for article_data in articles_data:
        existing = session.execute(
            select(Article.id).where(Article.content_hash == article_data["content_hash"])
        ).scalar_one_or_none()

        if existing:
            skipped += 1
            continue

        # Ensure source_type is set
        if "source_type" not in article_data:
            article_data["source_type"] = source_label

        article = Article(**article_data)
        session.add(article)
        inserted += 1

    session.commit()
    return inserted, skipped


@celery_app.task(name="app.tasks.scrape_task.scrape_inshorts", bind=True, max_retries=3)
def scrape_inshorts(self):
    """Scrape all sources and store articles.

    Despite the task name (kept for backward compatibility with beat schedule),
    this now runs the full multi-source pipeline:
      1. Inshorts (always)
      2. RSS feeds (always, free)
      3. NewsAPI (if key is set)
    """
    logger.info("🕷️ Starting multi-source scrape job")

    total_inserted = 0
    total_skipped = 0
    source_stats: dict[str, dict] = {}

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        session = _get_sync_session()

        # ── Source 1: Inshorts ────────────────────
        try:
            from app.services.scraper import scrape_all_categories

            inshorts_data = loop.run_until_complete(scrape_all_categories())
            for a in inshorts_data:
                a.setdefault("source_type", "inshorts")

            ins, skip = _insert_articles(session, inshorts_data, "inshorts")
            total_inserted += ins
            total_skipped += skip
            source_stats["inshorts"] = {"scraped": len(inshorts_data), "inserted": ins}
            logger.info(f"  Inshorts: {ins} inserted, {skip} skipped")
        except Exception as e:
            logger.error(f"Inshorts scrape failed: {e}")
            source_stats["inshorts"] = {"error": str(e)}

        # ── Source 2: RSS feeds ───────────────────
        try:
            from app.services.rss_scraper import scrape_all_rss

            rss_data = loop.run_until_complete(scrape_all_rss())
            ins, skip = _insert_articles(session, rss_data, "rss")
            total_inserted += ins
            total_skipped += skip
            source_stats["rss"] = {"scraped": len(rss_data), "inserted": ins}
            logger.info(f"  RSS feeds: {ins} inserted, {skip} skipped")
        except Exception as e:
            logger.error(f"RSS scrape failed: {e}")
            source_stats["rss"] = {"error": str(e)}

        # ── Source 3: NewsAPI (optional) ──────────
        try:
            from app.core import get_settings

            settings = get_settings()
            if settings.NEWSAPI_KEY:
                from app.services.newsapi_scraper import scrape_newsapi_headlines

                newsapi_data = loop.run_until_complete(scrape_newsapi_headlines())
                ins, skip = _insert_articles(session, newsapi_data, "newsapi")
                total_inserted += ins
                total_skipped += skip
                source_stats["newsapi"] = {"scraped": len(newsapi_data), "inserted": ins}
                logger.info(f"  NewsAPI: {ins} inserted, {skip} skipped")
            else:
                source_stats["newsapi"] = {"skipped": "no API key"}
        except Exception as e:
            logger.error(f"NewsAPI scrape failed: {e}")
            source_stats["newsapi"] = {"error": str(e)}

        session.close()

        logger.info(
            f"✅ Multi-source scrape complete: {total_inserted} inserted, "
            f"{total_skipped} duplicates skipped"
        )

        # Trigger analysis for new articles
        if total_inserted > 0:
            try:
                from app.tasks.analyze_task import analyze_pending_articles

                analyze_pending_articles.delay()
            except Exception as e:
                logger.warning(f"Failed to trigger analysis: {e}")

        return {
            "status": "complete",
            "total_inserted": total_inserted,
            "total_skipped": total_skipped,
            "sources": source_stats,
        }

    except Exception as e:
        logger.error(f"Scrape task failed: {e}")
        raise self.retry(exc=e, countdown=60) from e
    finally:
        loop.close()
