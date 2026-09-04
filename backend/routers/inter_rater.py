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
        completed_sessions = (
            await inter_rater_service.get_completed_sessions_for_inter_rating(user_id)
        )
        # Served from the pool cache the allocation just used, so no extra query.
        snapshot_id = await inter_rater_service.get_allocation_snapshot_id()
        return {
            "sessions": sessions,
            "max_sessions_per_user": inter_rater_service.sessions_per_user,
            "completed_sessions": completed_sessions,
            "allocation_snapshot_id": snapshot_id,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting inter-rater sessions: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve inter-rater sessions")


@router.get("/api/inter-rater/history")
async def get_inter_rater_history(request: Request):
    """
    Return the requesting reviewer's own recorded ratings for the current pool.

    Scoping is server-side and by `rater_id`: the reviewer's identity comes from
    the request, never from a parameter, so a reviewer cannot ask for anyone
    else's ratings. Read-only — there is no write counterpart.
    """
    try:
        from backend.services.inter_rater_service import inter_rater_service
        from backend.services.annotations_cache import annotations_cache

        if not inter_rater_service.is_enabled():
            raise HTTPException(status_code=404, detail="Inter-rater functionality is disabled")

        auth_method = get_auth_method()
        user_id = None
        if auth_method in ("cognito", "cloudflare"):
            user_id = _get_user_id_from_request(request)

        if not user_id:
            return {
                "ratings": [],
                "allocation_snapshot_id": None,
                "pool_span_ids": [],
            }

        # Citations are not rendered by the history view, and fetching them
        # costs a second Phoenix spans query for the REFERENCES spans
        # (phoenix_client._fetch_citations_by_qa_id). Skipping them also shares
        # the pool cache with the stats endpoint and the membership refresh,
        # so this call is far more often warm.
        pool_sessions, _, snapshot_id = await inter_rater_service._get_pool(
            include_citations=False
        )
        span_ids = [s["span_id"] for s in pool_sessions if s.get("span_id")]
        if not await annotations_cache.refresh_spans(span_ids):
            raise HTTPException(
                status_code=503,
                detail="Could not read your ratings. Please try again.",
            )

        ratings = []
        for session in pool_sessions:
            span_id = session.get("span_id")
            if not span_id:
                continue
            rating = annotations_cache.get_user_inter_rater_rating(span_id, user_id)
            if not rating:
                continue
            ratings.append({
                "span_id": span_id,
                "qa_id": session.get("qa_id"),
                "question": session.get("question"),
                "answer": session.get("answer"),
                **rating,
            })

        ratings.sort(key=lambda r: (r.get("timestamp") or ""))
        return {
            "ratings": ratings,
            "allocation_snapshot_id": snapshot_id,
            "pool_span_ids": span_ids,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting inter-rater history: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve your ratings")


@router.get("/api/inter-rater/stats")
async def get_inter_rater_stats(request: Request):
    """
    Get inter-rater statistics for the current user.
    """
    try:
        from backend.services.inter_rater_service import inter_rater_service

        if not inter_rater_service.is_enabled():
            return {"enabled": False, "default_ui": False}

        auth_method = get_auth_method()
        user_id = None

        if auth_method in ("cognito", "cloudflare"):
            user_id = _get_user_id_from_request(request)

        # If no authenticated user, return default stats
        if not user_id:
            return {"enabled": True, "available_sessions": 0, "completed_sessions": 0, "default_ui": inter_rater_service.default_ui}

        stats = await inter_rater_service.get_inter_rater_stats(user_id)
        return stats

    except Exception as e:
        logger.error(f"Error getting inter-rater stats: {type(e).__name__}")
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
