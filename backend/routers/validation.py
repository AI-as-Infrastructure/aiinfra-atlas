"""
Validation API endpoints for ATLAS.

Handles session validation using alternate LLM.
"""

import logging
import datetime
from typing import Dict, List, Optional, Any
from fastapi import APIRouter
from pydantic import BaseModel

from backend.services.validation_service import validation_service, SessionData

logger = logging.getLogger(__name__)

router = APIRouter()


class ValidationRequest(BaseModel):
    session_id: str
    qa_id: str
    question: str
    answer: str
    citations: List[Dict[str, Any]]
    metadata: Dict[str, Any]
    validation_mode: Optional[str] = None  # "default" or "alternate"


class ValidationResponse(BaseModel):
    success: bool
    message: str
    validation_result: Optional[Dict[str, Any]] = None
    markdown_export: Optional[str] = None
    validation_config: Optional[Dict[str, Any]] = None


@router.post("/api/validate_session", response_model=ValidationResponse)
async def validate_session(validation_request: ValidationRequest):
    """
    Validate a RAG session using an alternate LLM to provide structured feedback.

    This endpoint:
    1. Exports the session data to structured Markdown
    2. Sends it to a validation LLM (configured via .env)
    3. Returns structured feedback to guide human reviewers
    """

    # Check if validation is enabled
    if not validation_service.is_enabled():
        return ValidationResponse(
            success=False,
            message="Session validation is disabled",
            validation_config=validation_service.get_validation_config_info()
        )

    try:
        # Create session data object
        session_data = SessionData(
            session_id=validation_request.session_id,
            qa_id=validation_request.qa_id,
            question=validation_request.question,
            answer=validation_request.answer,
            citations=validation_request.citations,
            metadata=validation_request.metadata,
            timestamp=datetime.datetime.now().isoformat()
        )

        # Export session to Markdown
        markdown_export = validation_service.export_session_to_markdown(session_data)

        # Validate the session
        validation_result = validation_service.validate_session(
            session_data,
            validation_mode=validation_request.validation_mode
        )

        # Convert validation result to dict for response
        result_dict = {
            "session_id": validation_result.session_id,
            "qa_id": validation_result.qa_id,
            "validation_model": validation_result.validation_model,
            "validation_provider": validation_result.validation_provider,
            "validation_mode": validation_result.validation_mode,
            "feedback": validation_result.feedback,
            "structured_feedback": validation_result.structured_feedback,
            "validation_timestamp": validation_result.validation_timestamp,
            "processing_time": validation_result.processing_time
        }

        logger.info(f"Session validation completed for {validation_request.session_id} using {validation_result.validation_provider}/{validation_result.validation_model}")

        return ValidationResponse(
            success=True,
            message="Session validation completed successfully",
            validation_result=result_dict,
            markdown_export=markdown_export,
            validation_config=validation_service.get_validation_config_info()
        )

    except Exception as e:
        logger.error(f"Error during session validation: {e}")
        return ValidationResponse(
            success=False,
            message="Error during session validation",
            validation_config=validation_service.get_validation_config_info()
        )


@router.get("/api/validate_config")
async def get_validation_config():
    """
    Get current validation configuration information.
    """
    return validation_service.get_validation_config_info()
