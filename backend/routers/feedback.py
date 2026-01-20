"""
Feedback API endpoints for ATLAS.

Handles user feedback submission.
"""

import os
import logging
import datetime
from fastapi import APIRouter, Request

from backend.telemetry import using_session, log_user_feedback
from backend.telemetry.feedback import UserFeedback, FeedbackResponse
from backend.modules.auth import optional_user, is_cognito_enabled
from backend.modules.streaming import format_sse_message, create_error_message

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/api/feedback", response_model=FeedbackResponse)
async def submit_feedback(feedback: UserFeedback, request: Request):
    """
    Submit user feedback via HTTP.
    Primary feedback submission endpoint (WebSocket removed for security).
    """
    auth_required = os.getenv("VITE_USE_COGNITO_AUTH", "false").lower() == "true"

    try:
        # Authentication check - only enforce in environments with auth enabled
        if auth_required:
            auth_header = request.headers.get("Authorization")
            if not auth_header:
                logger.warning("Missing authentication for feedback submission")
                return FeedbackResponse(
                    message="Authentication required to submit feedback",
                    status="error"
                )
            user = await optional_user(request)
            if not user.get("authenticated", False):
                logger.warning("Unauthenticated feedback submission attempt")
                return FeedbackResponse(
                    message="Authentication required to submit feedback",
                    status="error"
                )
            # If inter-rater is enabled, set rater_id from authenticated user
            if os.getenv("INTER_RATER_ENABLED", "false").lower() == "true":
                feedback.rater_id = user.get("sub")

        # Get session ID and QA ID from the feedback
        session_id = feedback.session_id
        qa_id = feedback.qa_id

        # Validate session_id and qa_id
        if not session_id or not qa_id:
            logger.warning(f"Invalid feedback submission: missing session_id or qa_id")
            return FeedbackResponse(
                message="Invalid feedback submission: missing required identifiers",
                status="error"
            )

        logger.info(f"Received HTTP feedback for session {session_id}, qa {qa_id}")
        logger.info("Feedback metadata received (ids only)")

        # Format feedback data for telemetry
        feedback_data = {
            "relevance": feedback.relevance,
            "factual_accuracy": feedback.factual_accuracy,
            "source_quality": feedback.source_quality,
            "clarity": feedback.clarity,
            "question_rating": feedback.question_rating,
            "user_category": feedback.user_category,
            "tags": feedback.tags,
            "feedback_text": feedback.feedback_text,
            "model_answer": feedback.model_answer,
            "timestamp": feedback.timestamp or datetime.datetime.now().isoformat(),
            "source": "http_fallback",

            # New inline feedback fields
            "feedback_type": feedback.feedback_type,
            "sentiment": feedback.sentiment,
            "analysis_quality": feedback.analysis_quality,
            "difficulty": feedback.difficulty,
            "additional_comments": feedback.additional_comments,
            "faults": feedback.faults,

            # Rich context data from frontend
            "test_target": feedback.test_target,
            "question": feedback.question,
            "answer": feedback.answer,
            "citations": feedback.citations,
            "citation_count": len(feedback.citations) if feedback.citations else 0,

            # AI-Enhanced feedback fields
            "ai_validation": feedback.ai_validation,
            "ai_agreement": feedback.ai_agreement,
            "ratings": feedback.ratings,

            # Inter-rater reliability fields
            "is_inter_rater": feedback.is_inter_rater,
            "original_span_id": feedback.original_span_id,
            "rater_id": feedback.rater_id,
        }

        # Use the session context to ensure spans are properly associated
        with using_session(session_id):
            try:
                # Additional check for inter-rater duplicates at API level
                if feedback.is_inter_rater and feedback.rater_id and feedback.original_span_id:
                    try:
                        from backend.services.phoenix_client import phoenix_client
                        already_rated = await phoenix_client.check_user_already_rated(
                            feedback.original_span_id, feedback.rater_id
                        )
                        if already_rated:
                            sanitized_rater_id = feedback.rater_id[:8] + "..." if len(feedback.rater_id) > 8 else feedback.rater_id
                            sanitized_span_id = feedback.original_span_id[:8] + "..." if len(feedback.original_span_id) > 8 else feedback.original_span_id
                            logger.warning(f"User {sanitized_rater_id} attempted to rate span {sanitized_span_id} twice")
                            return FeedbackResponse(
                                message="You have already provided feedback for this session.",
                                status="error"
                            )
                    except Exception as dup_check_error:
                        logger.warning(f"Failed to check for duplicate inter-rater feedback: {dup_check_error}")

                # Log user feedback
                success = await log_user_feedback(session_id, qa_id, feedback_data)

                if success:
                    logger.info(f"HTTP Feedback recorded for session_id={session_id}, qa_id={qa_id}")

                    # If this is inter-rater feedback, invalidate the user's session cache
                    if feedback.is_inter_rater and feedback.rater_id:
                        try:
                            from backend.services.inter_rater_service import inter_rater_service
                            inter_rater_service.invalidate_user_cache(feedback.rater_id)
                            sanitized_rater_id = feedback.rater_id[:8] + "..." if len(feedback.rater_id) > 8 else feedback.rater_id
                            logger.debug(f"Invalidated inter-rater cache for user {sanitized_rater_id}")
                        except Exception as cache_error:
                            logger.warning(f"Failed to invalidate inter-rater cache: {cache_error}")

                    return FeedbackResponse(
                        message="Feedback received successfully",
                        status="success"
                    )
                else:
                    logger.error(f"Failed to record HTTP feedback for session_id={session_id}, qa_id={qa_id}")

                    if feedback.is_inter_rater:
                        error_msg = "Unable to submit inter-rater feedback. This may be due to a Phoenix API issue or the original session may no longer be available."
                        logger.error(f"Inter-rater feedback submission failed for original_span_id={feedback.original_span_id}")
                    else:
                        error_msg = "Unable to associate your feedback with this conversation. This may happen if the conversation data has expired."

                    return FeedbackResponse(
                        message=error_msg,
                        status="error"
                    )
            except Exception as e:
                logger.error(f"Error processing HTTP feedback: {e}")
                return FeedbackResponse(
                    message="Error processing feedback",
                    status="error"
                )
    except Exception as e:
        logger.error(f"Error in HTTP feedback endpoint: {e}")
        return FeedbackResponse(
            message="An error occurred processing your feedback",
            status="error"
        )
