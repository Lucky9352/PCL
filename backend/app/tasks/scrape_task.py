"""Celery task — periodic Inshorts scraper."""

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


@celery_app.task(name="app.tasks.scrape_task.scrape_inshorts", bind=True, max_retries=3)
def scrape_inshorts(self):
    """Scrape all Inshorts categories and store articles.

    Runs as a Celery periodic task every SCRAPE_INTERVAL_MINUTES.
    Deduplicates using content_hash before insertion.
    """
    logger.info("🕷️ Starting Inshorts scrape job")

    try:
        from app.db.models import Article
        from app.services.scraper import scrape_all_categories

        # Run async scraper in sync context
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        articles_data = loop.run_until_complete(scrape_all_categories())
        loop.close()

        if not articles_data:
            logger.warning("No articles scraped")
            return {"status": "complete", "scraped": 0, "inserted": 0}

        session = _get_sync_session()
        inserted = 0
        skipped = 0

        try:
            for article_data in articles_data:
                # Check for duplicate
                existing = session.execute(
                    select(Article.id).where(Article.content_hash == article_data["content_hash"])
                ).scalar_one_or_none()

                if existing:
                    skipped += 1
                    continue

                article = Article(**article_data)
                session.add(article)
                inserted += 1

            session.commit()
            logger.info(f"✅ Scrape complete: {inserted} inserted, {skipped} duplicates skipped")

            # Trigger analysis for new articles
            if inserted > 0:
                try:
                    from app.tasks.analyze_task import analyze_pending_articles

                    analyze_pending_articles.delay()
                except Exception as e:
                    logger.warning(f"Failed to trigger analysis: {e}")

        except Exception as e:
            session.rollback()
            logger.error(f"DB error during scrape: {e}")
            raise
        finally:
            session.close()

        return {"status": "complete", "scraped": len(articles_data), "inserted": inserted}

    except Exception as e:
        logger.error(f"Scrape task failed: {e}")
        raise self.retry(exc=e, countdown=60) from e
