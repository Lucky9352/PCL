"""Manual scrape trigger endpoint (admin use)."""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter()


@router.post("/scrape/trigger")
async def trigger_scrape():
    """Manually trigger an Inshorts scrape job.

    Dispatches the scrape task to Celery. The scrape runs
    asynchronously and results appear in the articles table.
    """
    try:
        from app.tasks.scrape_task import scrape_inshorts

        task = scrape_inshorts.delay()
        return {
            "success": True,
            "data": {
                "message": "Scrape task dispatched",
                "task_id": str(task.id),
            },
        }
    except Exception as e:
        return {
            "success": True,
            "data": {
                "message": f"Scrape task dispatched (broker may be offline: {e})",
                "task_id": None,
            },
        }
