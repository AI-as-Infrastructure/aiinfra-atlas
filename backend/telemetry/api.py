"""
API endpoints for telemetry in the ATLAS application.

This module provides FastAPI routes for telemetry-related functionality,
including Phoenix native feedback submission and debugging endpoints.
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime
from fastapi import APIRouter, Request, HTTPException

from .core import get_tracer, _phoenix_session, PHOENIX_AVAILABLE, is_telemetry_enabled
from .feedback import UserFeedback, FeedbackResponse, associate_feedback_with_spans

logger = logging.getLogger(__name__)

# Create router for telemetry endpoints
router = APIRouter()

@router.post("/api/feedback", response_model=FeedbackResponse)
async def submit_feedback(feedback: UserFeedback, request: Request):
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
        # Log reception of feedback
        logger.info(f"Received feedback for session {session_id}, qa {qa_id} from {client_ip}")
        
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
        
        # Use Phoenix native feedback association
        success = await associate_feedback_with_spans(session_id, qa_id, feedback_data)
        
        # Respond with success
        if success:
            # Success - we've successfully submitted the annotation
            logger.info(f"Feedback annotation recorded for session_id={session_id}, qa_id={qa_id}")
            return FeedbackResponse(
                message="Feedback recorded successfully",
                status="success"
            )
        else:
            logger.error(f"Failed to record feedback for session_id={session_id}, qa_id={qa_id}")
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
