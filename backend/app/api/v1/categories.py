"""Categories endpoint."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import Article, get_db

router = APIRouter()


@router.get("/categories")
async def list_categories(db: AsyncSession = Depends(get_db)):
    """Get all article categories with counts."""
    query = (
        select(Article.category, func.count(Article.id).label("count"))
        .where(Article.category.isnot(None))
        .group_by(Article.category)
        .order_by(func.count(Article.id).desc())
    )

    result = await db.execute(query)
    categories = [{"name": row.category, "count": row.count} for row in result.all()]

    return {"success": True, "data": categories}
