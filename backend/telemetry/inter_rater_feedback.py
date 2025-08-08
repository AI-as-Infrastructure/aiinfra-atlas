"""
Inter-rater reliability feedback system for ATLAS

This module provides inter-rater specific feedback functionality that is completely
separate from the regular feedback system. It's only loaded when INTER_RATER_ENABLED=true.
"""

import logging
import os
from typing import Dict, Any, Optional
# Note: BaseModel is imported from the base feedback module
from .feedback import UserFeedback, submit_span_annotation

logger = logging.getLogger(__name__)

class InterRaterFeedback(UserFeedback):
    """Inter-rater feedback model extending the base UserFeedback model."""
    
    # Inter-rater specific fields
    is_inter_rater: bool = True
    original_span_id: str  # Required - references the original span being re-rated
    # Optional here; backend derives from authenticated user and fills it in
    rater_id: Optional[str] = None

class InterRaterService:
    """Service for handling inter-rater feedback submissions."""
    
    def __init__(self):
        self.enabled = os.getenv("INTER_RATER_ENABLED", "false").lower() == "true"
    
    def is_enabled(self) -> bool:
        """Check if inter-rater functionality is enabled."""
        return self.enabled
    
    async def submit_inter_rater_feedback(self, session_id: str, qa_id: str, feedback_data: Dict[str, Any]) -> bool:
        """
        Submit inter-rater feedback directly to Phoenix using the original span ID.
        
        Args:
            session_id: Session ID (for compatibility, not used in inter-rater)
            qa_id: QA ID (for annotation naming)
            feedback_data: Inter-rater feedback data including original_span_id
            
        Returns:
            True if successful, False otherwise
        """
        logger.info(f"Processing inter-rater feedback for span {feedback_data.get('original_span_id')}")
        
        # For inter-rater feedback, we use the original_span_id directly
        target_span_id = feedback_data.get('original_span_id')
        
        if not target_span_id:
            logger.error("No original_span_id found in inter-rater feedback data")
            return False
        
        # Submit annotation directly to Phoenix using the original span ID
        success = submit_span_annotation(target_span_id, feedback_data, qa_id)
        
        if success:
            logger.info(f"Inter-rater feedback annotation submitted to span {target_span_id}")
            return True
        else:
            logger.error(f"Failed to submit inter-rater feedback annotation to span {target_span_id}")
            return False

# Global instance (will only be created if inter-rater is enabled)
_inter_rater_service = None

def get_inter_rater_service() -> Optional[InterRaterService]:
    """Get the inter-rater service instance, creating it if needed."""
    global _inter_rater_service
    
    if _inter_rater_service is None:
        service = InterRaterService()
        if service.is_enabled():
            _inter_rater_service = service
        else:
            return None
    
    return _inter_rater_service