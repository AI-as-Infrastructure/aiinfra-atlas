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
        self._cache_timeout = 300  # 5 minutes
    
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
        
        # Try cache first
        cached_sessions = await self._get_cached_sessions(user_id)
        if cached_sessions is not None:
            return cached_sessions
        
        try:
            from .phoenix_client import phoenix_client
            
            # Sanitize user_id for logging (show only first 8 chars + hash of rest)
            sanitized_user_id = user_id[:8] + "..." if len(user_id) > 8 else user_id
            logger.info(f"Querying Phoenix for inter-rater sessions for user {sanitized_user_id}")
            
            # Query Phoenix for sessions with original feedback
            sessions = await phoenix_client.query_spans_with_feedback(
                exclude_user_id=user_id,
                limit=self.sessions_per_user
            )
            
            # Filter sessions that haven't reached max ratings and user hasn't already rated
            filtered_sessions = []
            for session in sessions:
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
                    filtered_sessions.append(session)
            
            final_sessions = filtered_sessions[:self.sessions_per_user]
            
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
        
        try:
            # Get available sessions for this user
            available_sessions = await self.get_sessions_for_inter_rating(user_id)
            
            return {
                "enabled": True,
                "available_sessions": len(available_sessions),
                "completed_sessions": 0,  # This could be tracked if needed
                "max_sessions_per_user": self.sessions_per_user,
                "project_name": self.project_name
            }
            
        except Exception as e:
            logger.error(f"Error getting inter-rater stats: {e}")
            # Still return enabled=True since the service is configured to be enabled
            # The error just means no sessions are available
            return {
                "enabled": True,
                "available_sessions": 0,
                "completed_sessions": 0,
                "max_sessions_per_user": self.sessions_per_user,
                "project_name": self.project_name,
                "error": str(e)
            }
    
    def invalidate_user_cache(self, user_id: str):
        """
        Invalidate cached sessions for a user (call after they submit feedback).
        
        Args:
            user_id: The anonymous user ID from Cognito
        """
        cache_key = self._get_cache_key(user_id)
        if cache_key in self._session_cache:
            del self._session_cache[cache_key]
            sanitized_user_id = user_id[:8] + "..." if len(user_id) > 8 else user_id
            logger.debug(f"Invalidated cache for user {sanitized_user_id}")

# Global instance
inter_rater_service = InterRaterService()
