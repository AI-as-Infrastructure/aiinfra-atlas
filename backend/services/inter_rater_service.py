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
        
        # Simple in-memory cache for sessions (could be Redis in production)
        self._session_cache = {}
        self._cache_timeout = 60  # 1 minute - faster updates for development
        
        # Stats cache to avoid duplicate API calls during the same request
        self._stats_cache = {}
        self._stats_cache_timeout = 10  # 10 seconds for stats - faster updates
    
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
        Allocate sessions to a specific user using their Cognito user ID.
        This ensures different users get different non-overlapping sessions.
        
        Args:
            available_sessions: All sessions available for inter-rating
            user_id: The Cognito user ID (UUID) or dev user ID
            
        Returns:
            List of sessions allocated to this user
        """
        if not available_sessions:
            return []
        
        # Sort sessions by span_id for consistent ordering across users
        sorted_sessions = sorted(available_sessions, key=lambda x: x.get('span_id', ''))
        
        # Use the user_id to determine which sessions this user gets
        # For Cognito UUIDs, use the last few characters to get a number
        if user_id.startswith('dev_user_'):
            # For dev users, use IP-based allocation
            user_hash = hash(user_id) % len(sorted_sessions)
        else:
            # For Cognito UUIDs, use the hex characters to create a starting point
            try:
                # Take last 8 characters of UUID and convert from hex to int
                user_hash = int(user_id[-8:].replace('-', ''), 16) % len(sorted_sessions)
            except (ValueError, TypeError):
                # Fallback to simple hash if UUID format is unexpected
                user_hash = hash(user_id) % len(sorted_sessions)
        
        # Handle edge cases for uneven distribution
        total_sessions = len(sorted_sessions)
        max_sessions_to_allocate = min(self.sessions_per_user, total_sessions)
        
        # If we have fewer sessions than users * sessions_per_user, 
        # some users might get fewer sessions or none at all
        allocated_sessions = []
        
        if total_sessions == 0:
            return []
        
        # Calculate how many users could potentially get sessions
        potential_users = max(1, total_sessions // max_sessions_to_allocate)
        
        # If we have more sessions than one user can handle, distribute them
        if total_sessions >= self.sessions_per_user:
            # Normal case: allocate sessions starting from user's hash position
            for i in range(max_sessions_to_allocate):
                session_index = (user_hash + i) % total_sessions
                allocated_sessions.append(sorted_sessions[session_index])
        else:
            # Edge case: fewer sessions than sessions_per_user
            # Give this user sessions based on their position in the hash order
            user_position = user_hash % potential_users
            sessions_per_position = total_sessions // potential_users
            remainder_sessions = total_sessions % potential_users
            
            # Calculate start and end indices for this user
            start_idx = user_position * sessions_per_position
            # Some users get one extra session if there's a remainder
            if user_position < remainder_sessions:
                start_idx += user_position
                end_idx = start_idx + sessions_per_position + 1
            else:
                start_idx += remainder_sessions
                end_idx = start_idx + sessions_per_position
            
            # Allocate the sessions for this user
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
        
        Args:
            user_id: The anonymous user ID from Cognito
            
        Returns:
            List of session data for inter-rating
        """
        if not self.enabled:
            return []
        
        # Try cache first, but validate sessions still exist in Phoenix
        cached_sessions = await self._get_cached_sessions(user_id)
        if cached_sessions is not None:
            # Validate cached sessions still exist in Phoenix
            validated_sessions = await self._validate_sessions_in_phoenix(cached_sessions)
            
            # If validation removed sessions, update cache or refresh if too many were removed
            if len(validated_sessions) != len(cached_sessions):
                if len(validated_sessions) == 0:
                    # All cached sessions were deleted, clear cache and fetch fresh
                    self.invalidate_user_cache(user_id)
                    logger.info(f"All cached sessions were deleted, fetching fresh sessions for user {user_id[:8]}...")
                else:
                    # Some sessions were deleted, update cache with validated sessions
                    self._cache_sessions(user_id, validated_sessions)
                    return validated_sessions
            else:
                # All cached sessions are still valid
                return validated_sessions
        
        try:
            from .phoenix_client import phoenix_client
            
            # Sanitize user_id for logging (show only first 8 chars + hash of rest)
            sanitized_user_id = user_id[:8] + "..." if len(user_id) > 8 else user_id
            logger.info(f"Querying Phoenix for inter-rater sessions for user {sanitized_user_id}")
            
            # Query Phoenix for sessions with original feedback (get more to allow for allocation)
            all_sessions = await phoenix_client.query_spans_with_feedback(
                exclude_user_id=user_id,
                limit=self.sessions_per_user * 10  # Get more sessions to allow for proper allocation
            )
            
            # Filter sessions that haven't reached max ratings and user hasn't already rated
            available_sessions = []
            for session in all_sessions:
                # Check if user has already rated this session
                already_rated = await phoenix_client.check_user_already_rated(
                    session['span_id'], user_id
                )
                
                # Check if session has reached max ratings
                inter_rater_count = await phoenix_client.get_inter_rater_count(
                    session['span_id']
                )
                
                if not already_rated and inter_rater_count < self.max_ratings:
                    session['inter_rater_count'] = inter_rater_count
                    available_sessions.append(session)
            
            # Allocate sessions to this specific user using their user ID
            final_sessions = self._allocate_sessions_to_user(available_sessions, user_id)
            
            # Cache the results
            self._cache_sessions(user_id, final_sessions)
            
            logger.info(f"Found {len(final_sessions)} available sessions for user {sanitized_user_id}")
            return final_sessions
            
        except ValueError as e:
            # Re-raise ValueError (Phoenix data issues) to inform the user
            logger.error(f"Phoenix data error for inter-rating: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error retrieving sessions for inter-rating: {e}")
            # For unexpected errors, still raise to inform user
            raise ValueError(f"Failed to retrieve inter-rater sessions: {str(e)}")
    
    async def get_inter_rater_stats(self, user_id: str) -> Dict[str, Any]:
        """
        Get statistics about inter-rater sessions for a user.
        
        Args:
            user_id: The anonymous user ID from Cognito
            
        Returns:
            Statistics about available and completed sessions
        """
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
            # Get available sessions for this user
            available_sessions = await self.get_sessions_for_inter_rating(user_id)
            
            stats = {
                "enabled": True,
                "available_sessions": len(available_sessions),
                "completed_sessions": 0,  # This could be tracked if needed
                "max_sessions_per_user": self.sessions_per_user,
                "project_name": self.project_name
            }
            
            # Cache the stats
            self._stats_cache[stats_cache_key] = {
                'stats': stats,
                'timestamp': datetime.now().timestamp()
            }
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting inter-rater stats: {e}")
            # Still return enabled=True since the service is configured to be enabled
            # The error just means no sessions are available
            error_stats = {
                "enabled": True,
                "available_sessions": 0,
                "completed_sessions": 0,
                "max_sessions_per_user": self.sessions_per_user,
                "project_name": self.project_name,
                "error": str(e)
            }
            
            # Cache the error response for a shorter time
            self._stats_cache[stats_cache_key] = {
                'stats': error_stats,
                'timestamp': datetime.now().timestamp()
            }
            
            return error_stats
    
    def invalidate_user_cache(self, user_id: str):
        """
        Invalidate cached sessions for a user (call after they submit feedback).
        
        Args:
            user_id: The anonymous user ID from Cognito
        """
        cache_key = self._get_cache_key(user_id)
        stats_cache_key = f"stats_{user_id}"
        
        # Clear both session and stats cache
        if cache_key in self._session_cache:
            del self._session_cache[cache_key]
        if stats_cache_key in self._stats_cache:
            del self._stats_cache[stats_cache_key]
            
        sanitized_user_id = user_id[:8] + "..." if len(user_id) > 8 else user_id
        logger.debug(f"Invalidated cache for user {sanitized_user_id}")
    
    def clear_all_cache(self):
        """
        Clear all cached sessions. Useful when Phoenix data changes significantly.
        """
        self._session_cache.clear()
        self._stats_cache.clear()
        logger.info("Cleared all inter-rater session and stats cache")
    
    async def _validate_sessions_in_phoenix(self, sessions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Validate that cached sessions still exist in Phoenix and filter out deleted ones.
        
        Args:
            sessions: List of cached session data
            
        Returns:
            List of sessions that still exist in Phoenix
        """
        if not sessions:
            return []
        
        try:
            from .phoenix_client import phoenix_client
            
            # Get current spans from Phoenix to validate against
            current_spans = await phoenix_client.query_spans_with_feedback(limit=100)  # Get more spans for validation
            current_span_ids = {session['span_id'] for session in current_spans}
            
            # Filter cached sessions to only include those that still exist
            valid_sessions = []
            for session in sessions:
                if session.get('span_id') in current_span_ids:
                    valid_sessions.append(session)
                else:
                    logger.debug(f"Session with span_id {session.get('span_id')} no longer exists in Phoenix, removing from cache")
            
            if len(valid_sessions) != len(sessions):
                logger.info(f"Filtered out {len(sessions) - len(valid_sessions)} deleted sessions from cache")
            
            return valid_sessions
            
        except Exception as e:
            logger.warning(f"Failed to validate sessions in Phoenix: {e}, returning cached sessions as-is")
            return sessions

# Global instance
inter_rater_service = InterRaterService()
