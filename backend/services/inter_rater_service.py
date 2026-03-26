"""
Inter-rater reliability service for ATLAS.

This module provides functionality for managing inter-rater reliability sessions,
retrieving sessions for rating, and managing the inter-rater workflow.
"""

import logging
import os
from typing import List, Dict, Any, Optional
from datetime import datetime
import json
import hashlib

logger = logging.getLogger(__name__)

class InterRaterService:
    """Service for managing inter-rater reliability functionality."""

    def __init__(self):
        self.enabled = os.getenv("INTER_RATER_ENABLED", "false").lower() == "true"
        self.project_name = os.getenv("INTER_RATER_PROJECT", "atlas-hansard")
        self.max_ratings = int(os.getenv("INTER_RATER_MAX_RATINGS", "3"))
        self.sessions_per_user = int(os.getenv("INTER_RATER_SESSIONS_PER_USER", "5"))

        # In-memory cache for per-user session allocations
        self._session_cache = {}
        self._cache_timeout = 300  # 5 minutes

        # Stats cache
        self._stats_cache = {}
        self._stats_cache_timeout = 300  # 5 minutes

    def is_enabled(self) -> bool:
        """Check if inter-rater functionality is enabled."""
        return self.enabled

    def _get_cache_key(self, user_id: str) -> str:
        """Generate cache key for user sessions."""
        return f"inter_rater_sessions_{user_id}"

    def _is_cache_valid(self, cache_entry: Dict) -> bool:
        """Check if cache entry is still valid."""
        if not cache_entry:
            return False
        cache_time = cache_entry.get('timestamp', 0)
        current_time = datetime.now().timestamp()
        return (current_time - cache_time) < self._cache_timeout

    def _allocate_sessions_to_user(self, available_sessions: List[Dict[str, Any]], user_id: str) -> List[Dict[str, Any]]:
        """
        Allocate sessions to a specific user using their user ID.
        Ensures different users get different non-overlapping sessions.
        """
        if not available_sessions:
            return []

        sorted_sessions = sorted(available_sessions, key=lambda x: x.get('span_id', ''))

        if user_id.startswith('dev_user_'):
            user_hash = hash(user_id) % len(sorted_sessions)
        else:
            try:
                user_hash = int(user_id[-8:].replace('-', ''), 16) % len(sorted_sessions)
            except (ValueError, TypeError):
                user_hash = hash(user_id) % len(sorted_sessions)

        total_sessions = len(sorted_sessions)
        max_sessions_to_allocate = min(self.sessions_per_user, total_sessions)

        if total_sessions == 0:
            return []

        potential_users = max(1, total_sessions // max_sessions_to_allocate)

        if total_sessions >= self.sessions_per_user:
            allocated_sessions = []
            for i in range(max_sessions_to_allocate):
                session_index = (user_hash + i) % total_sessions
                allocated_sessions.append(sorted_sessions[session_index])
        else:
            user_position = user_hash % potential_users
            sessions_per_position = total_sessions // potential_users
            remainder_sessions = total_sessions % potential_users

            start_idx = user_position * sessions_per_position
            if user_position < remainder_sessions:
                start_idx += user_position
                end_idx = start_idx + sessions_per_position + 1
            else:
                start_idx += remainder_sessions
                end_idx = start_idx + sessions_per_position

            allocated_sessions = sorted_sessions[start_idx:end_idx]

        return allocated_sessions

    async def _get_cached_sessions(self, user_id: str) -> Optional[List[Dict[str, Any]]]:
        """Get sessions from cache if valid."""
        cache_key = self._get_cache_key(user_id)
        cache_entry = self._session_cache.get(cache_key)

        if self._is_cache_valid(cache_entry):
            sanitized_user_id = user_id[:8] + "..." if len(user_id) > 8 else user_id
            logger.debug(f"Returning cached sessions for user {sanitized_user_id}")
            return cache_entry['sessions']

        return None

    def _cache_sessions(self, user_id: str, sessions: List[Dict[str, Any]]):
        """Cache sessions for user."""
        cache_key = self._get_cache_key(user_id)
        self._session_cache[cache_key] = {
            'sessions': sessions,
            'timestamp': datetime.now().timestamp()
        }
        sanitized_user_id = user_id[:8] + "..." if len(user_id) > 8 else user_id
        logger.debug(f"Cached {len(sessions)} sessions for user {sanitized_user_id}")

    async def get_sessions_for_inter_rating(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Get sessions available for inter-rating by a specific user.

        Annotations are resolved from the local AnnotationsCache (no per-span
        HTTP calls). The only remote call is get_spans_dataframe() for the span
        data itself.
        """
        if not self.enabled:
            return []

        # Return cached sessions if valid
        cached_sessions = await self._get_cached_sessions(user_id)
        if cached_sessions is not None:
            return cached_sessions

        try:
            from .phoenix_client import phoenix_client
            from .annotations_cache import annotations_cache

            sanitized_user_id = user_id[:8] + "..." if len(user_id) > 8 else user_id
            logger.info(f"Querying Phoenix for inter-rater sessions for user {sanitized_user_id}")

            # query_spans_with_feedback already uses the annotations cache internally
            all_sessions = await phoenix_client.query_spans_with_feedback(
                exclude_user_id=user_id,
                limit=self.sessions_per_user * 10
            )

            # Filter: user hasn't already rated, and span hasn't reached max ratings
            # All lookups are local dict reads from the annotations cache
            available_sessions = []
            for session in all_sessions:
                span_id = session['span_id']

                already_rated = annotations_cache.check_user_already_rated(span_id, user_id)
                if already_rated:
                    continue

                inter_rater_count = annotations_cache.get_inter_rater_count(span_id)
                if inter_rater_count >= self.max_ratings:
                    continue

                session['inter_rater_count'] = inter_rater_count
                available_sessions.append(session)

            # Allocate sessions to this specific user
            final_sessions = self._allocate_sessions_to_user(available_sessions, user_id)

            # Cache the results
            self._cache_sessions(user_id, final_sessions)

            logger.info(f"Found {len(final_sessions)} available sessions for user {sanitized_user_id}")
            return final_sessions

        except ValueError as e:
            logger.error(f"Phoenix data error for inter-rating: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error retrieving sessions for inter-rating: {e}")
            raise ValueError(f"Failed to retrieve inter-rater sessions: {str(e)}")

    async def get_inter_rater_stats(self, user_id: str) -> Dict[str, Any]:
        """Get statistics about inter-rater sessions for a user."""
        if not self.enabled:
            return {"enabled": False}

        # Check stats cache first
        stats_cache_key = f"stats_{user_id}"
        if stats_cache_key in self._stats_cache:
            cache_entry = self._stats_cache[stats_cache_key]
            cache_time = cache_entry.get('timestamp', 0)
            current_time = datetime.now().timestamp()
            if (current_time - cache_time) < self._stats_cache_timeout:
                sanitized_user_id = user_id[:8] + "..." if len(user_id) > 8 else user_id
                logger.debug(f"Returning cached stats for user {sanitized_user_id}")
                return cache_entry['stats']

        try:
            available_sessions = await self.get_sessions_for_inter_rating(user_id)

            stats = {
                "enabled": True,
                "available_sessions": len(available_sessions),
                "completed_sessions": 0,
                "max_sessions_per_user": self.sessions_per_user,
                "project_name": self.project_name
            }

            self._stats_cache[stats_cache_key] = {
                'stats': stats,
                'timestamp': datetime.now().timestamp()
            }

            return stats

        except Exception as e:
            logger.error(f"Error getting inter-rater stats: {e}")
            error_stats = {
                "enabled": True,
                "available_sessions": 0,
                "completed_sessions": 0,
                "max_sessions_per_user": self.sessions_per_user,
                "project_name": self.project_name,
                "error": "Failed to retrieve inter-rater stats"
            }

            self._stats_cache[stats_cache_key] = {
                'stats': error_stats,
                'timestamp': datetime.now().timestamp()
            }

            return error_stats

    def invalidate_user_cache(self, user_id: str):
        """
        Invalidate caches after a user submits inter-rater feedback.

        Clears ALL users' session/stats caches (not just the submitter's)
        so that other concurrent users see updated already_rated and
        inter_rater_count values on their next request.
        """
        # Clear all users' caches — another user's view depends on this
        # user's rating (already_rated, inter_rater_count, max_ratings)
        self._session_cache.clear()
        self._stats_cache.clear()

        # Refresh the annotations cache so new feedback is visible immediately
        try:
            from .annotations_cache import annotations_cache
            annotations_cache.refresh()
        except Exception as e:
            logger.warning(f"Failed to refresh annotations cache: {e}")

        sanitized_user_id = user_id[:8] + "..." if len(user_id) > 8 else user_id
        logger.info(f"Cleared all caches after feedback from user {sanitized_user_id}")

    def clear_all_cache(self):
        """Clear all cached sessions."""
        self._session_cache.clear()
        self._stats_cache.clear()
        logger.info("Cleared all inter-rater session and stats cache")

# Global instance
inter_rater_service = InterRaterService()
