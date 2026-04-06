"""Pydantic schemas for dashboard statistics."""

from __future__ import annotations

from pydantic import BaseModel


class CategoryStats(BaseModel):
    """Stats for a single category."""

    category: str
    count: int
    avg_bias_score: float | None = None
    avg_trust_score: float | None = None
    avg_reliability_score: float | None = None


class SourceStats(BaseModel):
    """Stats for a single source."""

    source_name: str
    count: int
    credibility_tier: str | None = None
    avg_reliability_score: float | None = None


class DashboardStats(BaseModel):
    """Aggregate dashboard statistics."""

    total_articles: int = 0
    analyzed_articles: int = 0
    avg_bias_score: float | None = None
    avg_trust_score: float | None = None
    avg_reliability_score: float | None = None
    articles_by_category: list[CategoryStats] = []
    top_sources: list[SourceStats] = []
    bias_distribution: dict = {}
    trust_distribution: dict = {}
