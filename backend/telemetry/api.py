"""
API endpoints for telemetry in the ATLAS application.

This module provides FastAPI routes for telemetry-related functionality,
including Phoenix native feedback submission and debugging endpoints.
"""

import logging
import os
from typing import Dict, Any, Optional, Union
from datetime import datetime
from fastapi import APIRouter, Request, HTTPException

from .core import get_tracer, _phoenix_session, PHOENIX_AVAILABLE, is_telemetry_enabled
from .feedback import UserFeedback, FeedbackResponse, associate_feedback_with_spans

# Conditionally import inter-rater functionality
_inter_rater_enabled = os.getenv("INTER_RATER_ENABLED", "false").lower() == "true"

if _inter_rater_enabled:
    try:
        from .inter_rater_feedback import InterRaterFeedback, get_inter_rater_service
        INTER_RATER_AVAILABLE = True
    except ImportError as e:
        logger.warning(f"Inter-rater functionality requested but failed to import: {e}")
        INTER_RATER_AVAILABLE = False
else:
    INTER_RATER_AVAILABLE = False

logger = logging.getLogger(__name__)

# Create router for telemetry endpoints
router = APIRouter()

@router.post("/api/feedback", response_model=FeedbackResponse)
async def submit_feedback(feedback: Union[UserFeedback, InterRaterFeedback if INTER_RATER_AVAILABLE else UserFeedback], request: Request):
    """
    Submit user feedback for a session and question using Phoenix native evaluation system.
    """
    client_ip = request.client.host
    
    # Get trace ID from header if available
    trace_id = request.headers.get("X-Trace-Id", None)
    
    # If trace_id in header but not in feedback model, add it
    if trace_id and not feedback.trace_id:
        feedback.trace_id = trace_id
    
    # Get session ID and QA ID from the feedback
    session_id = feedback.session_id
    qa_id = feedback.qa_id
    
    # Check if telemetry is enabled (respects both system and user preference)
    telemetry_enabled = is_telemetry_enabled(request)
    
    if not telemetry_enabled:
        logger.info(f"Telemetry disabled - feedback submission skipped for session_id={session_id}, qa_id={qa_id}")
        return FeedbackResponse(
            message="Feedback received but telemetry is disabled. Feedback was not recorded.",
            status="success"
        )
    
    try:
        # Detect if this is inter-rater feedback
        is_inter_rater = (
            INTER_RATER_AVAILABLE and 
            hasattr(feedback, 'is_inter_rater') and
            feedback.is_inter_rater and
            hasattr(feedback, 'original_span_id') and
            feedback.original_span_id
        )
        
        # Log reception of feedback
        feedback_type = "inter-rater" if is_inter_rater else "regular"
        logger.info(f"Received {feedback_type} feedback for session {session_id}, qa {qa_id} from {client_ip}")
        
        # Format feedback data for Phoenix native evaluation system
        feedback_data = {
            # Original fields
            "relevance": feedback.relevance,
            "factual_accuracy": feedback.factual_accuracy,
            "source_quality": feedback.source_quality,
            "clarity": feedback.clarity,
            "question_rating": feedback.question_rating,
            "user_category": feedback.user_category,
            "tags": feedback.tags,
            "feedback_text": feedback.feedback_text,
            "model_answer": feedback.model_answer,
            "timestamp": datetime.now().isoformat(),
            "client_ip": client_ip,
            "trace_id": feedback.trace_id,  # Include trace_id for span correlation
            
            # New inline feedback fields
            "feedback_type": feedback.feedback_type,
            "sentiment": feedback.sentiment,
            "analysis_quality": feedback.analysis_quality,
            "difficulty": feedback.difficulty,
            "additional_comments": feedback.additional_comments,  # Missing field added
            "faults": feedback.faults,
            
            # Include rich context data from frontend
            "test_target": feedback.test_target,
            "question": feedback.question,
            "answer": feedback.answer,
            "citations": feedback.citations,
            
            # AI-Enhanced feedback fields
            "ai_validation": feedback.ai_validation,
            "ai_agreement": feedback.ai_agreement,
            "ratings": feedback.ratings
        }
        
        # Add inter-rater specific fields if this is inter-rater feedback
        if is_inter_rater:
            feedback_data.update({
                "is_inter_rater": True,
                "original_span_id": feedback.original_span_id,
                "rater_id": feedback.rater_id
            })
        
        # Route to appropriate feedback processing
        if is_inter_rater:
            # Use specialized inter-rater service
            inter_rater_service = get_inter_rater_service()
            if inter_rater_service:
                success = await inter_rater_service.submit_inter_rater_feedback(session_id, qa_id, feedback_data)
            else:
                logger.error("Inter-rater service not available")
                success = False
        else:
            # Use regular feedback association
            success = await associate_feedback_with_spans(session_id, qa_id, feedback_data)
        
        # Respond with success
        if success:
            # Success - we've successfully submitted the annotation
            logger.info(f"{feedback_type.title()} feedback annotation recorded for session_id={session_id}, qa_id={qa_id}")
            
            # For regular (non-inter-rater) feedback, clear inter-rater cache so new sessions become available
            if not is_inter_rater and INTER_RATER_AVAILABLE:
                try:
                    inter_rater_service = get_inter_rater_service()
                    if inter_rater_service and inter_rater_service.is_enabled():
                        inter_rater_service.clear_all_cache()
                        logger.debug("Cleared inter-rater cache after new regular feedback submission")
                except Exception as cache_error:
                    logger.warning(f"Failed to clear inter-rater cache after regular feedback: {cache_error}")
            
            return FeedbackResponse(
                message=f"{feedback_type.title()} feedback recorded successfully",
                status="success"
            )
        else:
            logger.error(f"Failed to record {feedback_type} feedback for session_id={session_id}, qa_id={qa_id}")
            if is_inter_rater:
                return FeedbackResponse(
                    message="Unable to submit inter-rater feedback. Please check that the original conversation is available and try again.",
                    status="error"
                )
            else:
                return FeedbackResponse(
                    message="Unable to associate your feedback with this conversation. This may happen if the conversation data has expired. Please try again or contact support if this issue persists.",
                    status="error"
                )
    except Exception as e:
        logger.error(f"Error processing feedback: {e}", exc_info=True)
        return FeedbackResponse(
            message=f"Error processing feedback: {str(e)}",
            status="error"
        )


def register_telemetry_api(app):
    """Register the telemetry API endpoints with the FastAPI app"""
    app.include_router(router)
    logger.debug("Registered telemetry API endpoints")
