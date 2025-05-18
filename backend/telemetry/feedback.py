"""
Feedback handling for the ATLAS application.

This module provides functions for collecting, validating, and submitting
user feedback to Phoenix Arize.
"""

import logging
from typing import Dict, Any, List, Tuple, Optional
from datetime import datetime
from pydantic import BaseModel

from opentelemetry.trace import SpanKind

from .core import create_span, tracer
from .spans import trace_operation, find_qa_span_id
from .constants import SpanAttributes, OpenInferenceSpanKind, SpanNames

logger = logging.getLogger(__name__)

# Pydantic model for feedback validation
class UserFeedback(BaseModel):
    session_id: str
    qa_id: str
    answer_rating: int
    citations_rating: int
    feedback_text: Optional[str] = None

class FeedbackResponse(BaseModel):
    message: str
    status: str

def get_rating_name(rating: int) -> str:
    """
    Convert a numeric rating to a descriptive label.
    
    Args:
        rating: Numeric rating (1-5)
        
    Returns:
        str: Descriptive label for the rating
    """
    if rating is None:
        return "not_rated"
    
    try:
        rating = int(rating)
        
        rating_labels = {
            1: "very_poor",
            2: "poor",
            3: "neutral",
            4: "good",
            5: "excellent"
        }
        
        return rating_labels.get(rating, f"invalid_rating_{rating}")
    except (ValueError, TypeError):
        return f"invalid_rating_{rating}"

def validate_feedback(feedback_data: Dict[str, Any]) -> Tuple[Dict[str, Any], List[str]]:
    """
    Validate feedback data and return a cleaned version.
    
    Args:
        feedback_data: Dictionary containing feedback data
        
    Returns:
        Tuple of (validated_data, warnings)
    """
    validated = {}
    warnings = []
    
    # Validate answer rating
    if "answer_rating" in feedback_data:
        try:
            rating = int(feedback_data["answer_rating"])
            if 1 <= rating <= 5:
                validated["answer_rating"] = rating
            else:
                warnings.append(f"Invalid answer rating: {rating}. Must be between 1 and 5.")
        except (ValueError, TypeError):
            warnings.append(f"Invalid answer rating format: {feedback_data['answer_rating']}. Must be an integer.")
    
    # Validate citations rating
    if "citations_rating" in feedback_data:
        try:
            rating = int(feedback_data["citations_rating"])
            if 1 <= rating <= 5:
                validated["citations_rating"] = rating
            else:
                warnings.append(f"Invalid citations rating: {rating}. Must be between 1 and 5.")
        except (ValueError, TypeError):
            warnings.append(f"Invalid citations rating format: {feedback_data['citations_rating']}. Must be an integer.")
    
    # Validate feedback text
    if "feedback_text" in feedback_data:
        text = str(feedback_data["feedback_text"]).strip()
        if len(text) <= 1000:  # Limit text length
            validated["feedback_text"] = text
        else:
            validated["feedback_text"] = text[:1000]
            warnings.append(f"Feedback text truncated to 1000 characters.")
    
    # Add timestamp if not present
    if "timestamp" in feedback_data:
        validated["timestamp"] = feedback_data["timestamp"]
    else:
        validated["timestamp"] = datetime.now().isoformat()
    
    return validated, warnings

def submit_span_annotation(span_id: str, feedback_data: Dict[str, Any], qa_id: str = None) -> bool:
    """
    Submit feedback as a span annotation to Phoenix using the span annotations API.
    
    Args:
        span_id: The ID of the span to annotate
        feedback_data: Dictionary containing feedback data
        qa_id: Question/answer ID to include in the annotation metadata
        
    Returns:
        bool: True if annotation was successfully submitted, False otherwise
    """
    import os
    import httpx
    import time
    from opentelemetry.trace import format_span_id
    
    # Get Phoenix API key from environment
    phoenix_api_key = None
    if os.getenv('PHOENIX_CLIENT_HEADERS', ''):
        headers_str = os.getenv('PHOENIX_CLIENT_HEADERS', '')
        if 'api_key=' in headers_str:
            phoenix_api_key = headers_str.split('api_key=')[1].split(',')[0].strip()
    
    # Fallback to PHOENIX_API_KEY for backward compatibility
    if not phoenix_api_key:
        phoenix_api_key = os.getenv('PHOENIX_API_KEY', '')
    
    if not phoenix_api_key:
        logger.error("No Phoenix API key found in environment variables")
        return False
    
    # Get Phoenix collector endpoint
    phoenix_endpoint = os.getenv('PHOENIX_COLLECTOR_ENDPOINT', 'https://app.phoenix.arize.com')
    if phoenix_endpoint.endswith('/v1/traces'):
        phoenix_endpoint = phoenix_endpoint[:-10]  # Remove '/v1/traces'
    
    # Construct annotation endpoint
    annotation_endpoint = f"{phoenix_endpoint}/v1/span_annotations?sync=false"
    
    # Extract feedback values
    answer_rating = feedback_data.get('answer_rating')
    citations_rating = feedback_data.get('citations_rating')
    feedback_text = feedback_data.get('feedback_text', '')
    
    # Use the answer rating for the main label and score
    label = get_rating_name(answer_rating)
    score = answer_rating / 5.0 if answer_rating is not None else 0.5
    
    # Ensure span_id is properly formatted using OpenTelemetry's format_span_id
    if isinstance(span_id, int):
        formatted_span_id = format_span_id(span_id)
    else:
        # Ensure it's a proper hex string with correct length
        if len(span_id) == 16:  # Already correctly formatted
            formatted_span_id = span_id
        else:
            try:
                # Try to convert to int and then format
                int_span_id = int(span_id, 16)
                formatted_span_id = format_span_id(int_span_id)
            except ValueError:
                # If conversion fails, use as is but log a warning
                logger.warning(f"Could not format span_id {span_id}, using as is")
                formatted_span_id = span_id
    
    logger.info(f"Using formatted span_id: {formatted_span_id} for annotation")
    
    # Generate a unique annotation ID that includes the QA ID for traceability
    annotation_id = f"feedback_{qa_id}_{int(time.time())}" if qa_id else f"feedback_{int(time.time())}"
    
    # Create a list to hold all annotations - we'll create separate ones for different ratings
    annotation_data = []
    
    # Add a dedicated annotation for user free text feedback if present
    if feedback_text:
        user_comment_annotation = {
            "id": f"{annotation_id}_user_comment",
            "span_id": formatted_span_id,
            "name": "user feedback",
            "annotator_kind": "HUMAN",
            "result": {
                "label": "user_comment",
                "explanation": feedback_text
            },
            "metadata": {
                "qa_id": qa_id,
                "timestamp": feedback_data.get('timestamp', datetime.now().isoformat())
            }
        }
        annotation_data.append(user_comment_annotation)

    # Optionally, keep rating annotations (without using explanation for Likert score, just label/score)
    if answer_rating is not None:
        answer_annotation = {
            "id": f"{annotation_id}_answer",
            "span_id": formatted_span_id,
            "name": "answer_rating",
            "annotator_kind": "HUMAN",
            "result": {
                "label": get_rating_name(answer_rating),
                "score": answer_rating / 5.0
            },
            "metadata": {
                "answer_rating": answer_rating,
                "citations_rating": citations_rating,
                "qa_id": qa_id,
                "timestamp": feedback_data.get('timestamp', datetime.now().isoformat())
            }
        }
        annotation_data.append(answer_annotation)
    
    if citations_rating is not None:
        citations_annotation = {
            "id": f"{annotation_id}_citations",
            "span_id": formatted_span_id,
            "name": "citations_rating",
            "annotator_kind": "HUMAN",
            "result": {
                "label": get_rating_name(citations_rating),
                "score": citations_rating / 5.0
            },
            "metadata": {
                "answer_rating": answer_rating,
                "citations_rating": citations_rating,
                "qa_id": qa_id,
                "timestamp": feedback_data.get('timestamp', datetime.now().isoformat())
            }
        }
        annotation_data.append(citations_annotation)
    
    # Construct annotation payload according to Phoenix API requirements
    annotation_payload = {
        "data": annotation_data
    }
    
    # Send annotation to Phoenix using httpx
    try:
        headers = {"api_key": phoenix_api_key}
        client = httpx.Client(timeout=10.0)  # Set a reasonable timeout
        
        response = client.post(
            annotation_endpoint,
            json=annotation_payload,
            headers=headers
        )
        
        if response.status_code == 200:
            logger.info(f"Successfully submitted annotation for span {formatted_span_id}")
            return True
        else:
            logger.error(f"Failed to submit annotation: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        logger.error(f"Error submitting annotation: {e}", exc_info=True)
        return False

def log_user_feedback(session_id: str, qa_id: str, feedback_data: Dict[str, Any]) -> bool:
    """
    Log user feedback for a specific QA interaction.
    
    Args:
        session_id: Session ID
        qa_id: Question/answer ID
        feedback_data: Dictionary containing feedback data
        
    Returns:
        bool: True if feedback was successfully logged, False otherwise
    """
    logger.info(f"DEBUG: log_user_feedback called with session_id={session_id}, qa_id={qa_id}")
    logger.info(f"DEBUG: feedback_data keys: {list(feedback_data.keys())}")
    if not tracer:
        logger.error("Phoenix tracer not initialized")
        return False
    
    if not session_id or not qa_id:
        logger.error("Missing session_id or qa_id in feedback")
        return False
    
    try:
        # Validate feedback data
        validated_feedback, warnings = validate_feedback(feedback_data)
        
        # Log any validation warnings
        if warnings:
            logger.warning(f"Feedback validation warnings: {warnings}")
        
        # Try to find the span ID for this QA interaction
        target_span_id = find_qa_span_id(session_id, qa_id)
        
        if not target_span_id:
            error_message = f"Unable to associate feedback with QA interaction {qa_id} in session {session_id}."
            logger.error(f"{error_message} The span was not properly registered when the QA interaction occurred.")
            
            # Return False to indicate failure - this will be reported to the user
            # The error message in the logs will help diagnose the issue
            return False
        else:
            # Submit feedback as a span annotation
            logger.info(f"Found target span ID: {target_span_id} for qa_id={qa_id}")
            success = submit_span_annotation(target_span_id, validated_feedback, qa_id)
            
            # Try to update the RAG pipeline span with the feedback
            try:
                # Get the parent span (RAG pipeline) using the target span association
                from backend.telemetry.core import get_span_by_id
                parent_span = get_span_by_id(target_span_id)
                
                if parent_span:
                    # Create a properly structured feedback object
                    answer_rating = validated_feedback.get("answer_rating")
                    citations_rating = validated_feedback.get("citations_rating")
                    feedback_text = validated_feedback.get("feedback_text", "")
                    
                    # Get rating names for better readability
                    answer_rating_name = get_rating_name(answer_rating)
                    citations_rating_name = get_rating_name(citations_rating)
                    
                    # Add feedback data to the parent span
                    parent_span.set_attribute("feedback.answer_rating", answer_rating)
                    parent_span.set_attribute("feedback.citations_rating", citations_rating)
                    parent_span.set_attribute("feedback.feedback_text", feedback_text)
                    parent_span.set_attribute("feedback.answer_rating_name", answer_rating_name)
                    parent_span.set_attribute("feedback.citations_rating_name", citations_rating_name)
                    parent_span.set_attribute("feedback.timestamp", datetime.now().isoformat())
                    
                    # Also store feedback in a properly nested structure for OpenInference
                    parent_span.set_attribute("openinference.feedback.answer_rating", answer_rating)
                    parent_span.set_attribute("openinference.feedback.citations_rating", citations_rating)
                    parent_span.set_attribute("openinference.feedback.feedback_text", feedback_text)
                    parent_span.set_attribute("openinference.feedback.answer_rating_name", answer_rating_name)
                    parent_span.set_attribute("openinference.feedback.citations_rating_name", citations_rating_name)
                    parent_span.set_attribute("openinference.feedback.timestamp", datetime.now().isoformat())
                    
                    logger.info(f"Successfully added feedback to parent span for qa_id {qa_id}")
                    return True
                else:
                    logger.warning(f"Could not find parent span with ID {target_span_id}")
                    return success
            except Exception as e:
                logger.warning(f"Could not update parent span with feedback: {e}")
                return success
    except Exception as e:
        logger.error(f"Failed to log user feedback: {e}", exc_info=True)
        return False

def associate_feedback_with_spans(qa_id, session_id, feedback_data):
    """
    Create a feedback processing span and ensure it's linked to the call_model span
    using Phoenix's native capabilities.
    
    Args:
        qa_id: The unique question/answer ID
        session_id: The session ID
        feedback_data: The feedback data to associate
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Get the rating values
        answer_rating = feedback_data.get("answer_rating")
        citations_rating = feedback_data.get("citations_rating")
        feedback_text = feedback_data.get("feedback_text", "")
        
        # Get rating names for better readability in Phoenix
        answer_rating_name = get_rating_name(answer_rating)
        citations_rating_name = get_rating_name(citations_rating)
        
        # Calculate normalized score (average of both ratings)
        normalized_score = (answer_rating + citations_rating) / 10.0 if answer_rating is not None and citations_rating is not None else 0.5
        
        # Create a properly structured feedback data object for the span
        feedback_object = {
            "answer_rating": answer_rating,
            "answer_rating_name": answer_rating_name,
            "citations_rating": citations_rating,
            "citations_rating_name": citations_rating_name,
            "normalized_score": normalized_score,
            "text": feedback_text,
            "timestamp": datetime.now().isoformat()
        }
        
        # Find the target span ID for this QA interaction
        target_span_id = find_qa_span_id(session_id, qa_id)
        if target_span_id:
            feedback_object["target_span_id"] = target_span_id
        
        # Create a span for the feedback processing
        with trace_operation(
            SpanNames.FEEDBACK_ANNOTATION,
            attributes={
                SpanAttributes.SESSION_ID: session_id,
                SpanAttributes.QA_ID: qa_id,
                "openinference.span.kind": "FEEDBACK",
                "openinference.feedback.answer_rating": answer_rating,
                "openinference.feedback.answer_rating_name": answer_rating_name,
                "openinference.feedback.citations_rating": citations_rating,
                "openinference.feedback.citations_rating_name": citations_rating_name,
                "openinference.feedback.normalized_score": normalized_score,
                "openinference.feedback.text": feedback_text,
                "target_span_id": feedback_data.get("target_span_id", ""),
                "timestamp": datetime.now().isoformat(),
                # Add individual feedback attributes
                "feedback.answer_rating": answer_rating,
                "feedback.answer_rating_name": answer_rating_name,
                "feedback.citations_rating": citations_rating,
                "feedback.citations_rating_name": citations_rating_name,
                "feedback.normalized_score": normalized_score,
                "feedback.text": feedback_text
            },
            session_id=session_id,
            qa_id=qa_id,
            openinference_kind="FEEDBACK"
        ) as span:
            logger.info(f"Created feedback annotation span for session {session_id}, qa_id {qa_id}")
            return True
    except Exception as e:
        logger.error(f"Error creating feedback annotation span: {e}", exc_info=True)
        return False

def get_rating_name(rating, rating_type='answer'):
    """
    Convert a numeric rating to a standardized text label.
    
    Args:
        rating: Numeric rating (typically 1-5)
        rating_type: Type of rating ('answer' or 'citations')
        
    Returns:
        str: Standardized text label for the rating
    """
    if rating is None:
        return "Not Rated"
    
    try:
        rating = int(rating)
        
        if rating == 1:
            return "Very Poor"
        elif rating == 2:
            return "Poor"
        elif rating == 3:
            return "Average"
        elif rating == 4:
            return "Good"
        elif rating == 5:
            return "Excellent"
        else:
            return f"Invalid Rating ({rating})"
    except (ValueError, TypeError):
        return f"Invalid Rating ({rating})"
