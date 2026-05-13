"""
Inter-rater reliability API endpoints for ATLAS.

Handles inter-rater session retrieval and statistics.
"""

import logging
from fastapi import APIRouter, Request, HTTPException

from backend.modules.auth import get_auth_method, optional_authenticated_user
from backend.services.anonymous_id_service import anonymous_id_service

logger = logging.getLogger(__name__)

router = APIRouter()


def _get_user_id_from_request(request: Request) -> str:
    """Extract anonymous user ID from authenticated request using auth dispatcher."""
    try:
        user = optional_authenticated_user(request)
        if user.get("authenticated"):
            return anonymous_id_service.get_anonymous_id_from_user_data(user)
    except Exception as e:
        logger.error(f"Error extracting user ID: {e}")
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

        auth_method = get_auth_method()
        user_id = None

        if auth_method in ("cognito", "cloudflare"):
            user_id = _get_user_id_from_request(request)

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

        auth_method = get_auth_method()
        user_id = None

        if auth_method in ("cognito", "cloudflare"):
            user_id = _get_user_id_from_request(request)

        # If no authenticated user, return default stats
        if not user_id:
            return {"enabled": True, "available_sessions": 0, "completed_sessions": 0}

        stats = await inter_rater_service.get_inter_rater_stats(user_id)
        return stats

    except Exception as e:
        logger.error(f"Error getting inter-rater stats: {type(e).__name__}")
        return {"enabled": False, "error": "Failed to retrieve inter-rater stats"}


@router.get("/api/inter-rater/debug")
async def debug_inter_rater(request: Request):
    """Diagnostic endpoint for inter-rater Phoenix query issues."""
    from backend.services.inter_rater_service import inter_rater_service
    from backend.services.phoenix_client import phoenix_client

    info = {
        "enabled": inter_rater_service.is_enabled(),
        "project_name": phoenix_client.project_name,
        "has_phoenix_client": phoenix_client.has_phoenix_client,
    }

    if not phoenix_client.has_phoenix_client:
        info["error"] = "Phoenix client not initialized"
        return info

    try:
        from datetime import datetime, timedelta
        end = datetime.now()
        start = end - timedelta(days=30)
        filter_expr = "name == 'com.atlas.rag.generation.response' and span_kind == 'LLM'"
        spans_df = phoenix_client.client.get_spans_dataframe(
            filter_expr,
            project_name=phoenix_client.project_name,
            start_time=start,
            end_time=end,
            timeout=30,
        )
        if spans_df is None or spans_df.empty:
            info["spans_found"] = 0
            info["columns"] = []
        else:
            info["spans_found"] = len(spans_df)
            info["columns"] = list(spans_df.columns)[:20]
            # Check first span for key attributes
            first = spans_df.iloc[0]
            info["sample_span_id"] = str(first.get("context.span_id", "MISSING"))
            info["sample_output"] = str(first.get("attributes.output.value", "MISSING"))[:100]
            info["sample_input"] = str(first.get("attributes.input.value", "MISSING"))[:100]
    except Exception as e:
        info["query_error"] = f"{type(e).__name__}: {e}"

    return info


@router.post("/api/inter-rater/refresh-cache")
async def refresh_inter_rater_cache(request: Request):
    """
    Force refresh of inter-rater session cache. Useful when Phoenix data has been modified.
    """
    try:
        from backend.services.inter_rater_service import inter_rater_service

        if not inter_rater_service.is_enabled():
            raise HTTPException(status_code=404, detail="Inter-rater functionality is disabled")

        auth_method = get_auth_method()
        user_id = None

        if auth_method in ("cognito", "cloudflare"):
            user_id = _get_user_id_from_request(request)

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
