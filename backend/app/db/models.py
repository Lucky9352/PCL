"""Database models for IndiaGround."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    DateTime,
    Float,
    ForeignKey,
    Index,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Article(Base):
    """Core articles table — stores scraped + analyzed news articles."""

    __tablename__ = "articles"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    synopsis: Mapped[str] = mapped_column(Text, nullable=False)
    author: Mapped[str | None] = mapped_column(Text, nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    category: Mapped[str | None] = mapped_column(String(100), nullable=True)
    source_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    inshorts_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    image_url: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Deduplication key — SHA-256(title + published_at)
    content_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)

    # Processing status: raw → preprocessed → analyzed → failed
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="raw")

    # ── NLP preprocessed data ─────────────────────
    entities: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    noun_phrases: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    language: Mapped[str | None] = mapped_column(String(10), nullable=True)
    is_duplicate: Mapped[bool | None] = mapped_column(default=False)
    duplicate_of: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)

    # ── Bias analysis (unBIAS module) ─────────────
    bias_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    bias_label: Mapped[str | None] = mapped_column(String(20), nullable=True)
    sentiment_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    sentiment_label: Mapped[str | None] = mapped_column(String(20), nullable=True)
    bias_types: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    flagged_tokens: Mapped[list | None] = mapped_column(JSONB, nullable=True)

    # ── Fact-check analysis (ClaimBuster module) ──
    trust_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    source_credibility_tier: Mapped[str | None] = mapped_column(String(20), nullable=True)
    top_claims: Mapped[list | None] = mapped_column(JSONB, nullable=True)

    # ── Aggregated reliability score ──────────────
    reliability_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    analysis_status: Mapped[str | None] = mapped_column(String(20), nullable=True, default=None)

    # ── Timestamps ────────────────────────────────
    scraped_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    analyzed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # ── Relationships ─────────────────────────────
    analysis_runs: Mapped[list[AnalysisRun]] = relationship(
        back_populates="article", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_articles_category", "category"),
        Index("ix_articles_status", "status"),
        Index("ix_articles_published_at", "published_at"),
        Index("ix_articles_reliability_score", "reliability_score"),
        Index("ix_articles_scraped_at", "scraped_at"),
    )


class ArchivedArticle(Base):
    """Archive table for articles older than 7 days — same schema as articles."""

    __tablename__ = "archived_articles"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    synopsis: Mapped[str] = mapped_column(Text, nullable=False)
    author: Mapped[str | None] = mapped_column(Text, nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    category: Mapped[str | None] = mapped_column(String(100), nullable=True)
    source_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    inshorts_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    image_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="raw")
    entities: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    noun_phrases: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    language: Mapped[str | None] = mapped_column(String(10), nullable=True)
    is_duplicate: Mapped[bool | None] = mapped_column(default=False)
    duplicate_of: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    bias_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    bias_label: Mapped[str | None] = mapped_column(String(20), nullable=True)
    sentiment_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    sentiment_label: Mapped[str | None] = mapped_column(String(20), nullable=True)
    bias_types: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    flagged_tokens: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    trust_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    source_credibility_tier: Mapped[str | None] = mapped_column(String(20), nullable=True)
    top_claims: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    reliability_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    analysis_status: Mapped[str | None] = mapped_column(String(20), nullable=True)
    scraped_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    analyzed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    archived_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class AnalysisRun(Base):
    """Records each analysis run for audit / debugging."""

    __tablename__ = "analysis_runs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    article_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("articles.id", ondelete="CASCADE"), nullable=False
    )
    model_name: Mapped[str] = mapped_column(String(200), nullable=False)
    model_version: Mapped[str | None] = mapped_column(String(100), nullable=True)
    raw_output: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    run_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    article: Mapped[Article] = relationship(back_populates="analysis_runs")

    __table_args__ = (Index("ix_analysis_runs_article_id", "article_id"),)


class Source(Base):
    """Indian news source credibility tiers."""

    __tablename__ = "sources"

    name: Mapped[str] = mapped_column(String(200), primary_key=True)
    credibility_tier: Mapped[str] = mapped_column(String(20), nullable=False, default="unknown")
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    bias_tendency: Mapped[str | None] = mapped_column(String(20), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
