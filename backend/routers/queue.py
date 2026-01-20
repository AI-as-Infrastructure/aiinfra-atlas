"""
Queue API endpoints for ATLAS.

Handles async queue statistics.
"""

import os
import logging
import datetime
from fastapi import APIRouter, HTTPException

logger = logging.getLogger(__name__)

router = APIRouter()

# Check async queue availability
environment = os.getenv("ENVIRONMENT", "development").lower()
async_queue_available = False

if environment in ["production", "staging"]:
    try:
        from backend.services.queue_manager import get_queue_manager
        async_queue_available = True
    except ImportError:
        pass
else:
    try:
        from backend.services.queue_manager import get_queue_manager
        async_queue_available = True
    except ImportError:
        pass


@router.get("/api/queue/stats")
async def get_queue_stats():
    """
    Get current queue statistics (admin endpoint).
    """
    if not async_queue_available:
        raise HTTPException(
            status_code=503,
            detail="Async processing not available. Redis queue not configured."
        )

    try:
        from backend.services.queue_manager import get_queue_manager
        queue_manager = get_queue_manager()
        stats = await queue_manager.get_queue_stats()

        return {
            "queue_stats": stats,
            "async_enabled": True,
            "timestamp": datetime.datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"Error getting queue stats: {e}")
        raise HTTPException(status_code=500, detail="Failed to get queue stats")
