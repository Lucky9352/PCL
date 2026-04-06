"""Health check endpoint."""

from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def health_check():
    """Application health check."""
    return {
        "success": True,
        "data": {
            "status": "healthy",
            "service": "IndiaGround API",
            "version": "0.1.0",
        },
    }
