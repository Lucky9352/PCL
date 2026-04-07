"""Manual scrape and maintenance triggers (admin / dev)."""

from __future__ import annotations

from fastapi import APIRouter, Query

router = APIRouter()


@router.post("/scrape/trigger")
async def trigger_scrape():
    """Dispatch multi-source scrape (Inshorts + RSS + optional NewsAPI) to Celery."""
    try:
        from app.tasks.scrape_task import scrape_inshorts

        task = scrape_inshorts.delay()
        return {
            "success": True,
            "data": {
                "message": "Multi-source scrape task dispatched",
                "task_id": str(task.id),
            },
        }
    except Exception as e:
        return {
            "success": False,
            "data": {
                "message": f"Task dispatch failed (broker may be offline: {e})",
                "task_id": None,
            },
        }


@router.post("/scrape/cluster-backfill")
async def trigger_cluster_backfill(limit: int = Query(default=200, ge=1, le=2000)):
    """Backfill story_cluster_id for analyzed articles missing it (after DB upgrade)."""
    try:
        from app.tasks.cluster_task import backfill_story_clusters

        task = backfill_story_clusters.delay(limit=limit)
        return {
            "success": True,
            "data": {
                "message": "Story cluster backfill dispatched",
                "task_id": str(task.id),
                "limit": limit,
            },
        }
    except Exception as e:
        return {
            "success": False,
            "data": {
                "message": str(e),
                "task_id": None,
            },
        }
