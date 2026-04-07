"""Story cluster API endpoints for cross-source comparison."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import Article, get_db
from app.db.models import StoryCluster

router = APIRouter(prefix="/stories")


@router.get("", response_model=dict)
async def list_stories(
    page_size: int = Query(default=20, ge=1, le=50),
    category: str | None = Query(default=None),
    min_sources: int = Query(
        default=2, ge=1, description="Minimum distinct outlets (unique_sources)"
    ),
    db: AsyncSession = Depends(get_db),
):
    """List story clusters where at least `min_sources` different outlets covered the story."""
    query = select(StoryCluster)

    if category:
        query = query.where(StoryCluster.category == category)

    query = query.order_by(StoryCluster.article_count.desc(), StoryCluster.created_at.desc()).limit(
        page_size * 4
    )

    result = await db.execute(query)
    clusters = [c for c in result.scalars().all() if len(c.unique_sources or []) >= min_sources][
        :page_size
    ]

    data = []
    for cluster in clusters:
        data.append(
            {
                "id": str(cluster.id),
                "representative_title": cluster.representative_title,
                "category": cluster.category,
                "article_count": cluster.article_count,
                "source_diversity": cluster.source_diversity,
                "bias_spectrum": cluster.bias_spectrum,
                "avg_reliability_score": cluster.avg_reliability_score,
                "avg_trust_score": cluster.avg_trust_score,
                "unique_sources": cluster.unique_sources,
                "created_at": cluster.created_at.isoformat() if cluster.created_at else None,
            }
        )

    return {"success": True, "data": data}


@router.get("/{cluster_id}", response_model=dict)
async def get_story(
    cluster_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get a single story cluster with all source articles."""
    cluster = await db.get(StoryCluster, cluster_id)
    if not cluster:
        raise HTTPException(status_code=404, detail="Story cluster not found")

    articles_result = await db.execute(
        select(Article)
        .where(Article.story_cluster_id == cluster_id)
        .order_by(Article.reliability_score.desc().nullslast())
    )
    articles = articles_result.scalars().all()

    articles_data = []
    for a in articles:
        articles_data.append(
            {
                "id": str(a.id),
                "title": a.title,
                "synopsis": a.synopsis,
                "source_name": a.source_name,
                "source_type": a.source_type,
                "source_url": a.source_url,
                "image_url": a.image_url,
                "published_at": a.published_at.isoformat() if a.published_at else None,
                "bias_score": a.bias_score,
                "bias_label": a.bias_label,
                "trust_score": a.trust_score,
                "reliability_score": a.reliability_score,
                "source_credibility_tier": a.source_credibility_tier,
                "sentiment_label": a.sentiment_label,
                "political_lean": a.political_lean,
                "cluster_similarity": a.cluster_similarity,
                "scraped_at": a.scraped_at.isoformat() if a.scraped_at else None,
                "author": a.author,
                "category": a.category,
                "analysis_status": a.analysis_status,
            }
        )

    return {
        "success": True,
        "data": {
            "cluster": {
                "id": str(cluster.id),
                "representative_title": cluster.representative_title,
                "category": cluster.category,
                "article_count": cluster.article_count,
                "source_diversity": cluster.source_diversity,
                "bias_spectrum": cluster.bias_spectrum,
                "avg_reliability_score": cluster.avg_reliability_score,
                "avg_trust_score": cluster.avg_trust_score,
                "unique_sources": cluster.unique_sources,
            },
            "articles": articles_data,
        },
    }
