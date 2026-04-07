"""Dashboard statistics endpoint."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import Article, get_db
from app.schemas.stats import CategoryStats, DashboardStats, SourceStats
from app.utils.source_credibility import get_source_credibility

router = APIRouter()


@router.get("/stats", response_model=dict)
async def get_dashboard_stats(db: AsyncSession = Depends(get_db)):
    """Get aggregate dashboard statistics."""

    # Total and analyzed counts
    total_result = await db.execute(select(func.count(Article.id)))
    total_articles = total_result.scalar() or 0

    analyzed_result = await db.execute(
        select(func.count(Article.id)).where(Article.analysis_status == "complete")
    )
    analyzed_articles = analyzed_result.scalar() or 0

    # Average scores (only for analyzed articles)
    avg_result = await db.execute(
        select(
            func.avg(Article.bias_score),
            func.avg(Article.trust_score),
            func.avg(Article.reliability_score),
        ).where(Article.analysis_status == "complete")
    )
    avg_row = avg_result.one_or_none()
    avg_bias = round(float(avg_row[0]), 3) if avg_row and avg_row[0] else None
    avg_trust = round(float(avg_row[1]), 3) if avg_row and avg_row[1] else None
    avg_reliability = round(float(avg_row[2]), 3) if avg_row and avg_row[2] else None

    # By category
    cat_query = (
        select(
            Article.category,
            func.count(Article.id).label("count"),
            func.avg(Article.bias_score).label("avg_bias"),
            func.avg(Article.trust_score).label("avg_trust"),
            func.avg(Article.reliability_score).label("avg_reliability"),
        )
        .where(Article.category.isnot(None))
        .group_by(Article.category)
        .order_by(func.count(Article.id).desc())
    )
    cat_result = await db.execute(cat_query)
    category_stats = [
        CategoryStats(
            category=row.category,
            count=row.count,
            avg_bias_score=round(float(row.avg_bias), 3) if row.avg_bias else None,
            avg_trust_score=round(float(row.avg_trust), 3) if row.avg_trust else None,
            avg_reliability_score=round(float(row.avg_reliability), 3)
            if row.avg_reliability
            else None,
        )
        for row in cat_result.all()
    ]

    # Top sources
    src_query = (
        select(
            Article.source_name,
            func.count(Article.id).label("count"),
            func.avg(Article.reliability_score).label("avg_reliability"),
        )
        .where(Article.source_name.isnot(None))
        .group_by(Article.source_name)
        .order_by(func.count(Article.id).desc())
        .limit(20)
    )
    src_result = await db.execute(src_query)
    top_sources = [
        SourceStats(
            source_name=row.source_name,
            count=row.count,
            credibility_tier=get_source_credibility(row.source_name or "")["tier"],
            avg_reliability_score=round(float(row.avg_reliability), 3)
            if row.avg_reliability
            else None,
        )
        for row in src_result.all()
    ]

    # Bias distribution (left, center, right, unclassified)
    bias_dist_query = (
        select(Article.bias_label, func.count(Article.id))
        .where(Article.bias_label.isnot(None))
        .group_by(Article.bias_label)
    )
    bias_dist_result = await db.execute(bias_dist_query)
    bias_distribution = {row[0]: row[1] for row in bias_dist_result.all()}

    # Trust distribution — half-open intervals [lo, hi) except last bucket [0.8, 1.0]
    t = Article.trust_score
    trust_dist_query = select(
        func.count(case(((t >= 0) & (t < 0.2), 1))).label("very_low"),
        func.count(case(((t >= 0.2) & (t < 0.4), 1))).label("low"),
        func.count(case(((t >= 0.4) & (t < 0.6), 1))).label("medium"),
        func.count(case(((t >= 0.6) & (t < 0.8), 1))).label("high"),
        func.count(case(((t >= 0.8) & (t <= 1.0), 1))).label("very_high"),
    ).where(t.isnot(None))
    trust_dist_result = await db.execute(trust_dist_query)
    trust_row = trust_dist_result.one()
    trust_distribution = {
        "0.0-0.2": trust_row.very_low,
        "0.2-0.4": trust_row.low,
        "0.4-0.6": trust_row.medium,
        "0.6-0.8": trust_row.high,
        "0.8-1.0": trust_row.very_high,
    }

    stats = DashboardStats(
        total_articles=total_articles,
        analyzed_articles=analyzed_articles,
        avg_bias_score=avg_bias,
        avg_trust_score=avg_trust,
        avg_reliability_score=avg_reliability,
        articles_by_category=category_stats,
        top_sources=top_sources,
        bias_distribution=bias_distribution,
        trust_distribution=trust_distribution,
    )

    return {"success": True, "data": stats}
