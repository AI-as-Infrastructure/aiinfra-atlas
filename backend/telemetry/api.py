"""
API endpoints for telemetry in the ATLAS application.

This module provides FastAPI routes for telemetry-related functionality,
including feedback submission and debugging endpoints.
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime
from fastapi import APIRouter, Request, HTTPException

from .core import tracer
from .feedback import UserFeedback, FeedbackResponse, log_user_feedback, validate_feedback


logger = logging.getLogger(__name__)

# Create router for telemetry endpoints
router = APIRouter()

@router.post("/api/feedback", response_model=FeedbackResponse)
async def submit_feedback(feedback: UserFeedback, request: Request):
    """
    Submit user feedback for a session and question.
    """
    client_ip = request.client.host
    
    # Get session ID and QA ID from the feedback
    session_id = feedback.session_id
    qa_id = feedback.qa_id
    
    try:
        # Log reception of feedback
        logger.debug(f"Received feedback for session {session_id}, qa {qa_id} from {client_ip}")
        
        # Format feedback data for OpenTelemetry
        feedback_data = {
            "answer_rating": feedback.answer_rating,
            "citations_rating": feedback.citations_rating, 
            "feedback_text": feedback.feedback_text,
            "timestamp": datetime.now().isoformat(),
            "client_ip": client_ip  # Store client IP for debugging
        }
        
        # Log user feedback
        success = log_user_feedback(session_id, qa_id, feedback_data)
        
        # Respond with success
        if success:
            logger.info(f"Feedback recorded for session_id={session_id}, qa_id={qa_id}")
            return FeedbackResponse(
                message="Feedback received successfully",
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


@router.get("/api/telemetry/status")
async def telemetry_status():
    """Check the status of the Phoenix telemetry integration"""
    try:
        # Check if Phoenix tracer is initialized
        phoenix_initialized = tracer is not None
        
        # Get Phoenix API key status
        import os
        phoenix_api_key = os.getenv('PHOENIX_API_KEY', '')
        client_api_key = None
        
        # Try extracting API key from PHOENIX_CLIENT_HEADERS
        if os.getenv('PHOENIX_CLIENT_HEADERS', ''):
            headers_str = os.getenv('PHOENIX_CLIENT_HEADERS', '')
            if 'api_key=' in headers_str:
                client_api_key = headers_str.split('api_key=')[1].split(',')[0].strip()
        
        # Get other Phoenix configuration
        phoenix_project_name = os.getenv('PHOENIX_PROJECT_NAME', '')
        phoenix_collector_endpoint = os.getenv('PHOENIX_COLLECTOR_ENDPOINT', '')
        otel_protocol = os.getenv('OTEL_EXPORTER_OTLP_PROTOCOL', '')
        otel_headers = os.getenv('OTEL_EXPORTER_OTLP_HEADERS', '')
        
        # Return status information
        return {
            "status": "ok",
            "phoenix_initialized": phoenix_initialized,
            "phoenix_project_name": phoenix_project_name,
            "phoenix_collector_endpoint": phoenix_collector_endpoint,
            "otel_protocol": otel_protocol,
            "api_key_format": "PHOENIX_CLIENT_HEADERS" if client_api_key else "PHOENIX_API_KEY" if phoenix_api_key else "None",
            "otel_headers_configured": bool(otel_headers),
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error checking telemetry status: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error checking telemetry status: {str(e)}")

def register_telemetry_api(app):
    """Register the telemetry API endpoints with the FastAPI app"""
    app.include_router(router)
    logger.debug("Registered telemetry API endpoints")
