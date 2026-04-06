"""Celery task — archive old articles (older than 7 days)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

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


@celery_app.task(name="app.tasks.cleanup_task.archive_old_articles")
def archive_old_articles():
    """Move articles older than 7 days to the archive table.

    Does NOT delete — moves to archived_articles for research dataset.
    """
    from app.db.models import ArchivedArticle, Article

    logger.info("📦 Starting article archival job")

    session = _get_sync_session()
    cutoff = datetime.now(UTC) - timedelta(days=7)
    archived = 0

    try:
        old_articles = (
            session.execute(select(Article).where(Article.scraped_at < cutoff)).scalars().all()
        )

        for article in old_articles:
            # Copy to archive
            archived_article = ArchivedArticle(
                id=article.id,
                title=article.title,
                synopsis=article.synopsis,
                author=article.author,
                published_at=article.published_at,
                category=article.category,
                source_name=article.source_name,
                source_url=article.source_url,
                inshorts_url=article.inshorts_url,
                image_url=article.image_url,
                content_hash=article.content_hash,
                status=article.status,
                entities=article.entities,
                noun_phrases=article.noun_phrases,
                language=article.language,
                is_duplicate=article.is_duplicate,
                duplicate_of=article.duplicate_of,
                bias_score=article.bias_score,
                bias_label=article.bias_label,
                sentiment_score=article.sentiment_score,
                sentiment_label=article.sentiment_label,
                bias_types=article.bias_types,
                flagged_tokens=article.flagged_tokens,
                trust_score=article.trust_score,
                source_credibility_tier=article.source_credibility_tier,
                top_claims=article.top_claims,
                reliability_score=article.reliability_score,
                analysis_status=article.analysis_status,
                scraped_at=article.scraped_at,
                analyzed_at=article.analyzed_at,
                created_at=article.created_at,
                updated_at=article.updated_at,
            )

            session.add(archived_article)
            session.delete(article)
            archived += 1

        session.commit()
        logger.info(f"📦 Archived {archived} articles older than 7 days")

    except Exception as e:
        session.rollback()
        logger.error(f"Archival failed: {e}")
    finally:
        session.close()

    return {"archived": archived}
