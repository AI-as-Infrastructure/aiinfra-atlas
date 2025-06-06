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
    
    # Check if telemetry is enabled
    telemetry_enabled = is_telemetry_enabled()
    
    if not telemetry_enabled:
        logger.info(f"Telemetry disabled - feedback submission skipped for session_id={session_id}, qa_id={qa_id}")
        return FeedbackResponse(
            message="Feedback received but telemetry is disabled. Feedback was not recorded.",
            status="success"
        )
    
    try:
        # Log reception of feedback
        logger.debug(f"Received feedback for session {session_id}, qa {qa_id} from {client_ip}")
        
        # Format feedback data for Phoenix native evaluation system
        feedback_data = {
            "relevance": feedback.relevance,
            "factual_accuracy": feedback.factual_accuracy,
            "source_quality": feedback.source_quality,
            "clarity": feedback.clarity,
            "question_rating": feedback.question_rating,
            "tags": feedback.tags,
            "feedback_text": feedback.feedback_text,
            "timestamp": datetime.now().isoformat(),
            "client_ip": client_ip,
            "trace_id": feedback.trace_id  # Include trace_id for span correlation
        }
        
        # Use Phoenix native feedback association
        success = associate_feedback_with_spans(session_id, qa_id, feedback_data)
        
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

@router.get("/api/telemetry/status")
async def telemetry_status():
    """Check the status of the Phoenix telemetry integration"""
    try:
        # Check if telemetry is enabled via environment variable
        telemetry_enabled = is_telemetry_enabled()
        
        # Check Phoenix native status
        phoenix_native_available = PHOENIX_AVAILABLE and _phoenix_session is not None
        
        # Check if tracer is initialized
        tracer_initialized = False
        try:
            tracer = get_tracer()
            tracer_initialized = tracer is not None
        except:
            pass
        
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
            "telemetry_enabled": telemetry_enabled,
            "telemetry_env_var": os.getenv('TELEMETRY_ENABLED', 'true'),
            "phoenix_native_available": phoenix_native_available and telemetry_enabled,
            "phoenix_session_active": _phoenix_session is not None and telemetry_enabled,
            "tracer_initialized": tracer_initialized and telemetry_enabled,
            "phoenix_project_name": phoenix_project_name,
            "phoenix_collector_endpoint": phoenix_collector_endpoint,
            "otel_protocol": otel_protocol,
            "api_key_format": "PHOENIX_CLIENT_HEADERS" if client_api_key else "PHOENIX_API_KEY" if phoenix_api_key else "None",
            "otel_headers_configured": bool(otel_headers),
            "feedback_system": "phoenix_native" if (phoenix_native_available and telemetry_enabled) else "opentelemetry_fallback" if telemetry_enabled else "disabled",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error checking telemetry status: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error checking telemetry status: {str(e)}")

def register_telemetry_api(app):
    """Register the telemetry API endpoints with the FastAPI app"""
    app.include_router(router)
    logger.debug("Registered telemetry API endpoints")
