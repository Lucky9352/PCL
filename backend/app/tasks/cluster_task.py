"""Celery task — backfill story cluster assignments for analyzed articles."""

from __future__ import annotations

from sqlalchemy import select

from app.core.celery_app import celery_app
from app.core.logging import logger


def _get_sync_session():
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    from app.core import get_settings

    settings = get_settings()
    engine = create_engine(settings.DATABASE_URL_SYNC, pool_pre_ping=True)
    return sessionmaker(bind=engine)()


@celery_app.task(name="app.tasks.cluster_task.backfill_story_clusters")
def backfill_story_clusters(limit: int = 200):
    """Assign story_cluster_id for analyzed articles missing it (e.g. pre-migration data)."""
    from app.db.models import Article
    from app.services.story_cluster_sync import assign_article_to_cluster

    session = _get_sync_session()
    updated = 0
    try:
        q = (
            select(Article)
            .where(
                Article.status == "analyzed",
                Article.story_cluster_id.is_(None),
                Article.is_duplicate.isnot(True),
            )
            .order_by(Article.scraped_at.desc())
            .limit(limit)
        )
        articles = session.execute(q).scalars().all()
        for article in articles:
            try:
                assign_article_to_cluster(session, article)
                session.commit()
                updated += 1
            except Exception as e:
                logger.warning(f"Backfill cluster failed for {article.id}: {e}")
                session.rollback()
        logger.info(f"Story cluster backfill: processed {updated} articles")
    finally:
        session.close()
    return {"updated": updated}
