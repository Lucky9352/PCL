"""Celery task — full analysis pipeline for pending articles."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime

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


@celery_app.task(name="app.tasks.analyze_task.analyze_pending_articles", bind=True)
def analyze_pending_articles(self):
    """Process all articles with status 'raw' through the full pipeline.

    Pipeline: preprocess → unbias → claimbuster → aggregate.
    """
    from app.db.models import AnalysisRun, Article
    from app.services.aggregator import aggregate_analysis
    from app.services.claimbuster import analyze_claims
    from app.services.preprocessor import (
        check_semantic_duplicate,
        compute_embedding,
        preprocess_article,
    )
    from app.services.unbias import analyze_bias

    logger.info("🔬 Starting analysis pipeline for pending articles")

    session = _get_sync_session()
    processed = 0
    failed = 0

    try:
        # Get raw articles
        raw_articles = (
            session.execute(select(Article).where(Article.status == "raw").limit(50))
            .scalars()
            .all()
        )

        if not raw_articles:
            logger.info("No pending articles to analyze")
            return {"processed": 0, "failed": 0}

        logger.info(f"Processing {len(raw_articles)} articles")

        # Get recent embeddings for dedup
        recent_articles = (
            session.execute(
                select(Article)
                .where(
                    Article.status.in_(["preprocessed", "analyzed"]),
                    Article.is_duplicate.is_(False),
                )
                .limit(200)
            )
            .scalars()
            .all()
        )

        existing_embeddings = []
        for ra in recent_articles:
            try:
                emb = compute_embedding(f"{ra.title}. {ra.synopsis}")
                if emb is not None:
                    existing_embeddings.append(emb)
            except Exception:
                continue

        for article in raw_articles:
            try:
                # ── Step 1: Preprocess ─────────────
                logger.info(f"Preprocessing: {article.title[:60]}...")
                prep = preprocess_article(article.title, article.synopsis)

                article.entities = prep["entities"]
                article.noun_phrases = prep["noun_phrases"]
                article.language = prep["language"]

                # Skip non-English articles
                if prep["language"] != "en" and prep["language"] != "unknown":
                    article.status = "preprocessed"
                    article.analysis_status = "skipped_non_english"
                    session.commit()
                    continue

                # ── Step 2: Semantic dedup ─────────
                new_emb = compute_embedding(f"{article.title}. {article.synopsis}")
                is_dup, sim_score = check_semantic_duplicate(new_emb, existing_embeddings)

                if is_dup:
                    article.is_duplicate = True
                    article.status = "preprocessed"
                    article.analysis_status = "skipped_duplicate"
                    logger.info(f"  → Near-duplicate (sim={sim_score:.3f}), skipping analysis")
                    session.commit()
                    continue

                if new_emb is not None:
                    existing_embeddings.append(new_emb)

                article.status = "preprocessed"
                session.commit()

                # ── Step 3: Bias analysis ──────────
                logger.info("  → Running bias analysis...")
                bias_result = analyze_bias(article.title, article.synopsis)

                # Log analysis run
                bias_run = AnalysisRun(
                    article_id=article.id,
                    model_name="unbias_hybrid",
                    model_version="0.1.0",
                    raw_output=bias_result,
                )
                session.add(bias_run)

                # ── Step 4: Fact-check analysis ────
                logger.info("  → Running local hybrid fact-check analysis...")
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                factcheck_result = loop.run_until_complete(
                    analyze_claims(article.title, article.synopsis, article.source_name)
                )
                loop.close()

                # Log analysis run
                factcheck_run = AnalysisRun(
                    article_id=article.id,
                    model_name="indiaground_hybrid_claim_detector",
                    model_version="0.1.0",
                    raw_output=factcheck_result,
                )
                session.add(factcheck_run)

                # ── Step 5: Aggregate ──────────────
                logger.info("  → Aggregating scores...")
                final = aggregate_analysis(bias_result, factcheck_result)

                # Update article with results
                article.bias_score = final["bias_score"]
                article.bias_label = final["bias_label"]
                article.sentiment_score = final["sentiment_score"]
                article.sentiment_label = final["sentiment_label"]
                article.bias_types = final["bias_types"]
                article.flagged_tokens = final["flagged_tokens"]
                article.trust_score = final["trust_score"]
                article.source_credibility_tier = final["source_credibility_tier"]
                article.top_claims = final["top_claims"]
                article.reliability_score = final["reliability_score"]
                article.analysis_status = final["analysis_status"]
                article.status = "analyzed"
                article.analyzed_at = datetime.now(UTC)

                session.commit()
                processed += 1

                logger.info(
                    f"  ✅ Complete: reliability={final['reliability_score']:.1f} "
                    f"bias={final['bias_score']:.3f} trust={final['trust_score']:.3f}"
                )

            except Exception as e:
                logger.error(f"Analysis failed for article {article.id}: {e}")
                article.status = "failed"
                article.analysis_status = "failed"
                session.commit()
                failed += 1
                continue

    except Exception as e:
        logger.error(f"Analysis pipeline error: {e}")
        session.rollback()
    finally:
        session.close()

    logger.info(f"🔬 Analysis complete: {processed} processed, {failed} failed")
    if locals().get("raw_articles") and len(raw_articles) == 50:
        analyze_pending_articles.delay()

    return {"processed": processed, "failed": failed}
