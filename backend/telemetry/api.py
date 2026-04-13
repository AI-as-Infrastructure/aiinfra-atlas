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
from backend.modules.auth import get_auth_method, optional_authenticated_user
from backend.services.anonymous_id_service import anonymous_id_service
from .feedback import UserFeedback, FeedbackResponse, associate_feedback_with_spans

logger = logging.getLogger(__name__)

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

# Create router for telemetry endpoints
router = APIRouter()

@router.post("/api/feedback", response_model=FeedbackResponse)
async def submit_feedback(feedback: Union[InterRaterFeedback, UserFeedback] if INTER_RATER_AVAILABLE else UserFeedback, request: Request):
    """
    Submit user feedback for a session and question using Phoenix native evaluation system.
    """
    # Client IP intentionally not logged or exported (privacy)
    
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
        # Detect if this is inter-rater feedback by model type when available
        is_inter_rater = False
        if INTER_RATER_AVAILABLE:
            try:
                from .inter_rater_feedback import InterRaterFeedback as IRF
                is_inter_rater = isinstance(feedback, IRF) and bool(getattr(feedback, 'original_span_id', None))
            except Exception:
                is_inter_rater = bool(getattr(feedback, 'is_inter_rater', False) and getattr(feedback, 'original_span_id', None))
        
        # Log reception of feedback
        feedback_type = "inter-rater" if is_inter_rater else "regular"
        logger.info(f"Received {feedback_type} feedback for session {session_id}, qa {qa_id}")
        
        # Resolve anonymous user ID from auth dispatcher
        anon_user_id = None
        auth_method = get_auth_method()

        try:
            user = optional_authenticated_user(request)
            if user.get("authenticated"):
                anon_user_id = anonymous_id_service.get_anonymous_id_from_user_data(user)
                logger.info(f"Generated anonymous user ID for feedback: {anon_user_id[:12]}... (auth_method={auth_method})")
            else:
                logger.info(f"Auth method '{auth_method}' - no authenticated identity for feedback")
        except Exception as e:
            logger.error(f"Exception during user ID extraction for feedback: {type(e).__name__}")
            anon_user_id = None

        # Log final result for debugging inter-rater issues
        logger.info(f"Feedback user ID extraction result: user_id={'present' if anon_user_id else 'NONE'}, auth_method={auth_method}")

        # Validate user_id for inter-rater functionality
        inter_rater_enabled = os.getenv("INTER_RATER_ENABLED", "false").lower() == "true"
        if inter_rater_enabled and not anon_user_id:
            logger.error("CRITICAL: Inter-rater is enabled but no user_id captured for feedback - this will break inter-rater allocation!")
            logger.error(f"Auth details: auth_method={auth_method}")
            
            # For regular feedback, we can still proceed but warn
            if not is_inter_rater:
                logger.warning("Regular feedback proceeding without user_id - user's own ratings may appear in their inter-rater list")
            else:
                # For inter-rater feedback, this should not happen as it requires auth
                logger.error("Inter-rater feedback without user_id - this should not be possible")

        # Format feedback data for Phoenix native evaluation system
        feedback_data = {
            # Original fields
            "relevance": feedback.relevance,
            "factual_accuracy": feedback.factual_accuracy,
            "corpus_fidelity": getattr(feedback, 'corpus_fidelity', None),
            "source_quality": feedback.source_quality,
            "clarity": feedback.clarity,
            "question_rating": feedback.question_rating,
            "user_category": feedback.user_category,
            "user_type": getattr(feedback, 'user_type', None),
            "tags": feedback.tags,
            "feedback_text": feedback.feedback_text,
            "model_answer": feedback.model_answer,
            "timestamp": datetime.now().isoformat(),
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
            "ratings": feedback.ratings,
            # Attach anonymized user id for original feedback to support exclusion downstream
            "user_id": anon_user_id
        }
        
        # Add inter-rater specific fields if this is inter-rater feedback
        if is_inter_rater:
            # Inter-rating requires authentication; enforce and set rater_id from backend
            if not anon_user_id:
                logger.warning("Inter-rater feedback attempted without authenticated user")
                return FeedbackResponse(
                    message="Authentication required for inter-rater feedback",
                    status="error"
                )
            feedback_data.update({
                "is_inter_rater": True,
                "original_span_id": feedback.original_span_id,
                "rater_id": anon_user_id
            })
        
        # Route to feedback processing (use unified path)
        success = await associate_feedback_with_spans(session_id, qa_id, feedback_data)
        
        # Respond with success
        if success:
            # Success - we've successfully submitted the annotation
            logger.info(f"{feedback_type.title()} feedback annotation recorded for session_id={session_id}, qa_id={qa_id}")
            
            # For regular (non-inter-rater) feedback, clear inter-rater cache so new sessions become available
            if not is_inter_rater:
                try:
                    # Use the allocation service for cache management
                    from backend.services.inter_rater_service import inter_rater_service as allocation_ir_service
                    if allocation_ir_service and allocation_ir_service.is_enabled():
                        allocation_ir_service.clear_all_cache()
                        logger.debug("Cleared inter-rater cache after new regular feedback submission")
                except Exception as cache_error:
                    logger.warning(f"Failed to clear inter-rater cache after regular feedback: {cache_error}")
            else:
                # For inter-rater feedback, record the rating locally so check_user_already_rated()
                # sees it instantly (before Phoenix propagation), then invalidate user's cache
                try:
                    if anon_user_id and feedback.original_span_id:
                        from backend.services.annotations_cache import annotations_cache as ac
                        ac.record_user_rating(feedback.original_span_id, anon_user_id)
                    if anon_user_id:
                        from backend.services.inter_rater_service import inter_rater_service as allocation_ir_service
                        if allocation_ir_service and allocation_ir_service.is_enabled():
                            allocation_ir_service.invalidate_user_cache(anon_user_id)
                except Exception as cache_error:
                    logger.warning(f"Failed to update cache after inter-rater feedback: {cache_error}")
            
            return FeedbackResponse(
                message=f"{feedback_type.title()} feedback recorded successfully",
                status="success"
            )
        else:
            logger.error(f"Failed to record {feedback_type} feedback for session_id={session_id}, qa_id={qa_id}")
            if is_inter_rater:
                # Invalidate cache so deleted/unavailable span is dropped on next load
                try:
                    if anon_user_id:
                        from backend.services.inter_rater_service import inter_rater_service as allocation_ir_service
                        if allocation_ir_service and allocation_ir_service.is_enabled():
                            allocation_ir_service.invalidate_user_cache(anon_user_id)
                except Exception as cache_error:
                    logger.warning(f"Failed to invalidate cache after inter-rater failure: {cache_error}")
                return FeedbackResponse(
                    message="This inter-rating session is no longer available.",
                    status="session_unavailable"
                )
            else:
                return FeedbackResponse(
                    message="Unable to associate your feedback with this conversation. This may happen if the conversation data has expired. Please try again or contact support if this issue persists.",
                    status="error"
                )
    except Exception as e:
        logger.error(f"Error processing feedback: {type(e).__name__}")
        return FeedbackResponse(
            message="Error processing feedback",
            status="error"
        )


def register_telemetry_api(app):
    """Register the telemetry API endpoints with the FastAPI app"""
    app.include_router(router)
    logger.debug("Registered telemetry API endpoints")


