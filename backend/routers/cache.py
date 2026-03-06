"""
Cache API endpoints for ATLAS.

Handles prompt cache statistics and management.
"""

import logging
from datetime import datetime
from fastapi import APIRouter, Request, HTTPException

from backend.modules.auth import get_auth_method, get_authenticated_user

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/api/cache/stats")
async def get_cache_stats(request: Request):
    """Return prompt cache statistics for monitoring."""
    auth_method = get_auth_method()
    if auth_method in ("cognito", "cloudflare"):
        get_authenticated_user(request)  # Enforce auth; raises 401 if invalid

    try:
        from backend.modules.prompt_cache import get_cache_statistics
        cache_stats = get_cache_statistics()

        return {
            "cache_statistics": cache_stats,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting cache statistics: {e}")
        return {
            "error": "Failed to retrieve cache statistics",
            "cache_statistics": {},
            "timestamp": datetime.now().isoformat()
        }


@router.post("/api/cache/clear")
async def clear_cache(request: Request):
    """Clear the prompt cache."""
    auth_method = get_auth_method()
    if auth_method in ("cognito", "cloudflare"):
        get_authenticated_user(request)  # Enforce auth; raises 401 if invalid

    try:
        from backend.modules.prompt_cache import clear_prompt_cache
        clear_prompt_cache()

        logger.info("Prompt cache cleared via API")

        return {
            "message": "Prompt cache cleared successfully",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error clearing cache: {e}")
        return {
            "error": "Failed to clear cache",
            "timestamp": datetime.now().isoformat()
        }
