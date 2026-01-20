"""
Cache API endpoints for ATLAS.

Handles prompt cache statistics and management.
"""

import os
import logging
from datetime import datetime
from fastapi import APIRouter, Request, HTTPException

from backend.modules.auth import verify_cognito_token

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/api/cache/stats")
async def get_cache_stats(request: Request):
    """Return prompt cache statistics for monitoring."""
    auth_required = os.getenv("VITE_USE_COGNITO_AUTH", "false").lower() == "true"

    if auth_required:
        auth_header = request.headers.get("Authorization")
        if not auth_header:
            raise HTTPException(
                status_code=401,
                detail="Authorization header required"
            )

        try:
            token = auth_header.split(" ")[1] if " " in auth_header else auth_header
        except (IndexError, AttributeError):
            raise HTTPException(
                status_code=401,
                detail="Invalid authorization header format"
            )

        user = await verify_cognito_token(token)

        if not user.get("authenticated", False):
            raise HTTPException(
                status_code=403,
                detail="Unauthorized access to cache statistics"
            )

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
    auth_required = os.getenv("VITE_USE_COGNITO_AUTH", "false").lower() == "true"

    if auth_required:
        auth_header = request.headers.get("Authorization")
        if not auth_header:
            raise HTTPException(
                status_code=401,
                detail="Authorization header required"
            )

        try:
            token = auth_header.split(" ")[1] if " " in auth_header else auth_header
        except (IndexError, AttributeError):
            raise HTTPException(
                status_code=401,
                detail="Invalid authorization header format"
            )

        user = await verify_cognito_token(token)

        if not user.get("authenticated", False):
            raise HTTPException(
                status_code=403,
                detail="Unauthorized access to cache management"
            )

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
