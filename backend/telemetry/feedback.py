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
from .spans import trace_operation, find_qa_span_id, find_session_root_span_id
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
    Submit feedback as span annotations to Phoenix, preserving each type of feedback separately.
    
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
    annotation_endpoint = f"{phoenix_endpoint}/v1/span_annotations?sync=true"
    
    # Extract feedback values
    answer_rating = feedback_data.get('answer_rating')
    citations_rating = feedback_data.get('citations_rating')
    feedback_text = feedback_data.get('feedback_text', '')
    timestamp = feedback_data.get('timestamp', datetime.now().isoformat())
    
    # Format the span ID correctly for Phoenix
    if isinstance(span_id, int):
        from opentelemetry.trace import format_span_id
        formatted_span_id = format_span_id(span_id)
    else:
        formatted_span_id = span_id
    
    # Create a list to hold all annotations - we'll create separate ones for each type of feedback
    annotations = []
    
    # Create answer rating annotation if provided
    if answer_rating is not None:
        answer_annotation = {
            "id": f"feedback_answer_{qa_id}_{int(time.time())}",
            "span_id": formatted_span_id,
            "name": "answer_rating",
            "annotator_kind": "HUMAN",
            "result": {
                "label": f"answer_rating_{answer_rating}",
                "score": answer_rating / 5.0
            },
            "metadata": {
                "rating_type": "answer",
                "rating_value": answer_rating,
                "qa_id": qa_id,
                "timestamp": timestamp
            }
        }
        annotations.append(answer_annotation)
    
    # Create citation rating annotation if provided
    if citations_rating is not None:
        citation_annotation = {
            "id": f"feedback_citation_{qa_id}_{int(time.time())}",
            "span_id": formatted_span_id,
            "name": "citation_rating",
            "annotator_kind": "HUMAN",
            "result": {
                "label": f"citation_rating_{citations_rating}",
                "score": citations_rating / 5.0
            },
            "metadata": {
                "rating_type": "citations",
                "rating_value": citations_rating,
                "qa_id": qa_id,
                "timestamp": timestamp
            }
        }
        annotations.append(citation_annotation)
    
    # Create text feedback annotation if provided
    if feedback_text:
        text_annotation = {
            "id": f"feedback_text_{qa_id}_{int(time.time())}",
            "span_id": formatted_span_id,
            "name": "feedback_text",
            "annotator_kind": "HUMAN",
            "result": {
                "label": "user_comment",
                "explanation": feedback_text
            },
            "metadata": {
                "feedback_type": "text",
                "qa_id": qa_id,
                "timestamp": timestamp
            }
        }
        annotations.append(text_annotation)
    
    # Construct annotation payload
    annotation_payload = {
        "data": annotations
    }
    
    # Send annotation to Phoenix
    try:
        headers = {"api_key": phoenix_api_key}
        client = httpx.Client(timeout=10.0)
        
        # Log details for debugging
        logger.info(f"Sending {len(annotations)} annotations to Phoenix for span {formatted_span_id}")
        
        response = client.post(
            annotation_endpoint,
            json=annotation_payload,
            headers=headers
        )
        
        if response.status_code >= 200 and response.status_code < 300:
            logger.info(f"Successfully submitted {len(annotations)} annotations for span {formatted_span_id}")
            return True
        else:
            logger.error(f"Failed to submit annotations: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        logger.error(f"Error submitting annotations: {e}", exc_info=True)
        return False

def log_user_feedback(session_id: str, qa_id: str, feedback_data: Dict[str, Any]) -> bool:
    """
    Log user feedback to telemetry by adding annotations to the existing spans.
    Associates different feedback types with the appropriate spans:
    - answer_rating -> response span (com.atlas.rag.generation.response)
    - citations_rating -> references span (com.atlas.rag.references)
    - feedback_text -> added to both spans for context
    
    Args:
        session_id: Session ID 
        qa_id: Question/answer ID
        feedback_data: Feedback data dictionary
        
    Returns:
        True if feedback was logged successfully, False otherwise
    """
    if not session_id or not qa_id:
        logger.warning(f"Cannot log feedback: missing session_id or qa_id")
        return False
    
    try:
        # Import the global registry directly to check available spans
        from backend.telemetry.spans import _span_registry
        
        # Log available spans for debugging
        if session_id in _span_registry:
            available_spans = list(_span_registry[session_id].keys())
            logger.info(f"Available spans for session {session_id}: {available_spans}")
        
        # Find the response span for answer rating
        response_span_id = find_qa_span_id(session_id, f"{qa_id}_response")
        
        # Find the references span for citations rating
        references_span_id = find_qa_span_id(session_id, f"{qa_id}_references")
        
        # If specific spans not found, fall back to the main QA span
        main_qa_span_id = find_qa_span_id(session_id, qa_id)
        
        if not response_span_id and not references_span_id and not main_qa_span_id:
            logger.warning(f"No valid spans found for feedback: session_id={session_id}, qa_id={qa_id}")
            return False
        
        success = True
        annotations_count = 0
        
        # Associate answer rating with response span (or fall back to main span)
        if 'answer_rating' in feedback_data:
            target_span_id = response_span_id or main_qa_span_id
            if target_span_id:
                # Create answer feedback subset
                answer_feedback = {
                    'answer_rating': feedback_data['answer_rating']
                }
                
                # Include feedback text with answer rating if present
                if feedback_data.get('feedback_text'):
                    answer_feedback['feedback_text'] = feedback_data['feedback_text']
                
                logger.info(f"Associating answer_rating with span {target_span_id} (response span)")
                answer_success = submit_span_annotation(target_span_id, answer_feedback, qa_id)
                success = success and answer_success
                annotations_count += 1
                
                if answer_success:
                    logger.info(f"Successfully associated answer_rating with span {target_span_id}")
                else:
                    logger.warning(f"Failed to associate answer_rating with span {target_span_id}")
            else:
                logger.warning(f"No target span found for answer_rating")
        
        # Associate citations rating with references span
        if 'citations_rating' in feedback_data:
            target_span_id = references_span_id or main_qa_span_id
            if target_span_id:
                # Create citations feedback subset
                citations_feedback = {
                    'citations_rating': feedback_data['citations_rating']
                }
                
                logger.info(f"Associating citations_rating with span {target_span_id} (references span)")
                citations_success = submit_span_annotation(target_span_id, citations_feedback, qa_id)
                success = success and citations_success
                annotations_count += 1
                
                if citations_success:
                    logger.info(f"Successfully associated citations_rating with span {target_span_id}")
                else:
                    logger.warning(f"Failed to associate citations_rating with span {target_span_id}")
            else:
                logger.warning(f"No target span found for citations_rating")
        
        # Associate standalone feedback text (if not already included with answer rating)
        if feedback_data.get('feedback_text') and not 'answer_rating' in feedback_data:
            # Determine the best span for text feedback - prefer response span over reference span
            target_span_id = response_span_id or main_qa_span_id
            if target_span_id:
                # Create text feedback subset
                text_feedback = {
                    'feedback_text': feedback_data['feedback_text']
                }
                
                logger.info(f"Associating feedback_text with span {target_span_id}")
                text_success = submit_span_annotation(target_span_id, text_feedback, qa_id)
                success = success and text_success
                annotations_count += 1
                
                if text_success:
                    logger.info(f"Successfully associated feedback_text with span {target_span_id}")
                else:
                    logger.warning(f"Failed to associate feedback_text with span {target_span_id}")
            else:
                logger.warning(f"No target span found for feedback_text")
        
        logger.info(f"Total annotations associated with spans: {annotations_count}")
        return success
    except Exception as e:
        logger.error(f"Error logging feedback: {e}", exc_info=True)
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
