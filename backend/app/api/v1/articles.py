"""Articles CRUD endpoints with cursor-based pagination."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import Article, get_db
from app.schemas.article import (
    ArticleAnalysis,
    ArticleCard,
    ArticleDetail,
    ArticleListResponse,
    PaginationMeta,
)

router = APIRouter(prefix="/articles")


@router.get("", response_model=ArticleListResponse)
async def list_articles(
    page_size: int = Query(default=20, ge=1, le=100, description="Items per page"),
    cursor: str | None = Query(default=None, description="Cursor for next page (article ID)"),
    category: str | None = Query(default=None, description="Filter by category"),
    bias: str | None = Query(default=None, description="Filter by bias label"),
    trust_min: float | None = Query(default=None, ge=0, le=1, description="Min trust score"),
    status: str | None = Query(default=None, description="Filter by status"),
    search: str | None = Query(default=None, description="Search in title/synopsis"),
    db: AsyncSession = Depends(get_db),
):
    """List articles with cursor-based pagination and filters."""
    query = select(Article).where(Article.is_duplicate.is_(False) | Article.is_duplicate.is_(None))

    # Apply filters
    if category:
        query = query.where(Article.category == category)
    if bias:
        query = query.where(Article.bias_label == bias)
    if trust_min is not None:
        query = query.where(Article.trust_score >= trust_min)
    if status:
        query = query.where(Article.status == status)
    if search:
        search_term = f"%{search}%"
        query = query.where(Article.title.ilike(search_term) | Article.synopsis.ilike(search_term))

    # Cursor-based pagination using scraped_at + id
    if cursor:
        try:
            cursor_id = uuid.UUID(cursor)
            cursor_article = await db.get(Article, cursor_id)
            if cursor_article:
                query = query.where(
                    (Article.scraped_at < cursor_article.scraped_at)
                    | ((Article.scraped_at == cursor_article.scraped_at) & (Article.id < cursor_id))
                )
        except (ValueError, AttributeError):
            raise HTTPException(status_code=400, detail="Invalid cursor") from None

    # Order by newest first
    query = query.order_by(Article.scraped_at.desc(), Article.id.desc())
    query = query.limit(page_size + 1)  # Fetch one extra to check has_more

    result = await db.execute(query)
    articles = list(result.scalars().all())

    has_more = len(articles) > page_size
    if has_more:
        articles = articles[:page_size]

    # Get total count (cached for performance)
    count_query = select(func.count(Article.id))
    if category:
        count_query = count_query.where(Article.category == category)
    total_result = await db.execute(count_query)
    total_count = total_result.scalar()

    next_cursor = str(articles[-1].id) if has_more and articles else None

    return ArticleListResponse(
        success=True,
        data=[ArticleCard.model_validate(a) for a in articles],
        meta=PaginationMeta(
            next_cursor=next_cursor,
            has_more=has_more,
            total_count=total_count,
        ),
    )


@router.get("/{article_id}", response_model=dict)
async def get_article(
    article_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get full article detail by ID."""
    article = await db.get(Article, article_id)
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")

    return {
        "success": True,
        "data": ArticleDetail.model_validate(article),
    }


@router.get("/{article_id}/analysis", response_model=dict)
async def get_article_analysis(
    article_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get detailed analysis for an article."""
    article = await db.get(Article, article_id)
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")

    if article.analysis_status != "complete":
        return {
            "success": True,
            "data": None,
            "message": f"Analysis not yet complete. Status: {article.analysis_status or article.status}",
        }

    return {
        "success": True,
        "data": ArticleAnalysis(
            article_id=article.id,
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
            analyzed_at=article.analyzed_at,
        ),
    }
