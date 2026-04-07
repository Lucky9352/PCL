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


def _base_filter(
    query,
    category: str | None,
    bias: str | None,
    trust_min: float | None,
    status: str | None,
    search: str | None,
):
    """Apply shared filters used by both the list query and the count query."""
    query = query.where(Article.is_duplicate.is_(False) | Article.is_duplicate.is_(None))
    if category:
        query = query.where(Article.category == category)
    if bias:
        query = query.where(Article.bias_label == bias)
    if trust_min is not None:
        query = query.where(Article.trust_score >= trust_min)
    if status:
        query = query.where(Article.status == status)
    if search:
        term = f"%{search}%"
        query = query.where(Article.title.ilike(term) | Article.synopsis.ilike(term))
    return query


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
    query = _base_filter(select(Article), category, bias, trust_min, status, search)

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

    query = query.order_by(Article.scraped_at.desc(), Article.id.desc())
    query = query.limit(page_size + 1)

    result = await db.execute(query)
    articles = list(result.scalars().all())

    has_more = len(articles) > page_size
    if has_more:
        articles = articles[:page_size]

    count_query = _base_filter(
        select(func.count(Article.id)), category, bias, trust_min, status, search
    )
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
        "data": ArticleAnalysis.model_validate(article),
    }
