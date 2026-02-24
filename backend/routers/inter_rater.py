"""
Inter-rater reliability API endpoints for ATLAS.

Handles inter-rater session retrieval and statistics.
"""

import os
import logging
from fastapi import APIRouter, Request, HTTPException

from backend.modules.auth import verify_cognito_token, is_cognito_enabled

logger = logging.getLogger(__name__)

router = APIRouter()


def _get_user_id_from_request(request: Request, auth_header: str) -> str:
    """Extract anonymous user ID from authenticated request."""
    token = auth_header.split(" ", 1)[1] if " " in auth_header else auth_header
    payload = verify_cognito_token(token)
    if payload and payload.get("sub"):
        from backend.services.anonymous_id_service import anonymous_id_service
        user = {"sub": payload.get("sub"), "authenticated": True}
        return anonymous_id_service.get_anonymous_id_from_user_data(user)
    return None


@router.get("/api/inter-rater/sessions")
async def get_inter_rater_sessions(request: Request):
    """
    Get sessions available for inter-rating by the current user.
    """
    try:
        from backend.services.inter_rater_service import inter_rater_service

        if not inter_rater_service.is_enabled():
            raise HTTPException(status_code=404, detail="Inter-rater functionality is disabled")

        auth_required = os.getenv("VITE_USE_COGNITO_AUTH", "false").lower() == "true"
        user_id = None

        if auth_required and is_cognito_enabled():
            auth_header = request.headers.get("Authorization")
            if auth_header:
                user_id = _get_user_id_from_request(request, auth_header)

        # If no authenticated user, return empty
        if not user_id:
            return {"sessions": []}

        sessions = await inter_rater_service.get_sessions_for_inter_rating(user_id)
        return {"sessions": sessions}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting inter-rater sessions: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve inter-rater sessions")


@router.get("/api/inter-rater/stats")
async def get_inter_rater_stats(request: Request):
    """
    Get inter-rater statistics for the current user.
    """
    try:
        from backend.services.inter_rater_service import inter_rater_service

        if not inter_rater_service.is_enabled():
            return {"enabled": False}

        auth_required = os.getenv("VITE_USE_COGNITO_AUTH", "false").lower() == "true"
        user_id = None

        if auth_required and is_cognito_enabled():
            auth_header = request.headers.get("Authorization")
            if auth_header:
                user_id = _get_user_id_from_request(request, auth_header)

        # If no authenticated user, return default stats
        if not user_id:
            return {"enabled": True, "available_sessions": 0, "completed_sessions": 0}

        stats = await inter_rater_service.get_inter_rater_stats(user_id)
        return stats

    except Exception as e:
        logger.error(f"Error getting inter-rater stats: {e}")
        return {"enabled": False, "error": "Failed to retrieve inter-rater stats"}


@router.post("/api/inter-rater/refresh-cache")
async def refresh_inter_rater_cache(request: Request):
    """
    Force refresh of inter-rater session cache. Useful when Phoenix data has been modified.
    """
    try:
        from backend.services.inter_rater_service import inter_rater_service

        if not inter_rater_service.is_enabled():
            raise HTTPException(status_code=404, detail="Inter-rater functionality is disabled")

        auth_required = os.getenv("VITE_USE_COGNITO_AUTH", "false").lower() == "true"
        user_id = None

        if auth_required and is_cognito_enabled():
            auth_header = request.headers.get("Authorization")
            if auth_header:
                user_id = _get_user_id_from_request(request, auth_header)

        # If no authenticated user, return default response
        if not user_id:
            return {"enabled": True, "available_sessions": 0, "completed_sessions": 0}

        # Clear cache for this user and force fresh fetch
        inter_rater_service.invalidate_user_cache(user_id)

        # Fetch fresh sessions
        sessions = await inter_rater_service.get_sessions_for_inter_rating(user_id)

        return {
            "message": "Cache refreshed successfully",
            "sessions_found": len(sessions),
            "status": "success"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error refreshing inter-rater cache: {e}")
        raise HTTPException(status_code=500, detail="Failed to refresh inter-rater cache")
