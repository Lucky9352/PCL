"""Pydantic schemas for article API responses."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel


class ArticleCard(BaseModel):
    """Compact article representation for list/feed views."""

    id: uuid.UUID
    title: str
    synopsis: str
    author: str | None = None
    published_at: datetime | None = None
    category: str | None = None
    source_name: str | None = None
    image_url: str | None = None
    reliability_score: float | None = None
    bias_score: float | None = None
    bias_label: str | None = None
    trust_score: float | None = None
    sentiment_label: str | None = None
    analysis_status: str | None = None
    scraped_at: datetime

    model_config = {"from_attributes": True}


class ArticleDetail(ArticleCard):
    """Full article with all fields."""

    source_url: str | None = None
    inshorts_url: str | None = None
    content_hash: str
    status: str
    entities: dict | None = None
    noun_phrases: list | None = None
    language: str | None = None
    is_duplicate: bool | None = False
    sentiment_score: float | None = None
    bias_types: list | None = None
    flagged_tokens: list | None = None
    source_credibility_tier: str | None = None
    top_claims: list | None = None
    analyzed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class ArticleAnalysis(BaseModel):
    """Detailed analysis breakdown for an article."""

    article_id: uuid.UUID
    bias_score: float | None = None
    bias_label: str | None = None
    sentiment_score: float | None = None
    sentiment_label: str | None = None
    bias_types: list[str] | None = None
    flagged_tokens: list[dict] | None = None
    trust_score: float | None = None
    source_credibility_tier: str | None = None
    top_claims: list[dict] | None = None
    reliability_score: float | None = None
    analysis_status: str | None = None
    analyzed_at: datetime | None = None

    model_config = {"from_attributes": True}


class PaginationMeta(BaseModel):
    """Cursor-based pagination metadata."""

    next_cursor: str | None = None
    has_more: bool = False
    total_count: int | None = None


class ArticleListResponse(BaseModel):
    """Paginated article list response."""

    success: bool = True
    data: list[ArticleCard]
    meta: PaginationMeta
