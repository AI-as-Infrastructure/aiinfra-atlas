"""
Phoenix Native Feedback System for ATLAS

This module implements the correct Phoenix Arize approach for associating
feedback with spans using Phoenix's native span evaluation system.
"""

import logging
import json
from pydantic import BaseModel, ConfigDict
from typing import Optional, List, Dict, Any
from .spans import find_qa_span_id
from datetime import datetime

logger = logging.getLogger(__name__)

class UserFeedback(BaseModel):
    """User feedback submission model"""
    model_config = ConfigDict(extra='ignore')
    
    session_id: str
    qa_id: str
    relevance: Optional[int] = None
    factual_accuracy: Optional[bool] = None
    source_quality: Optional[int] = None
    clarity: Optional[int] = None
    tags: Optional[List[str]] = []
    feedback_text: Optional[str] = None
    
    # Additional rich data from frontend
    test_target: Optional[Dict[str, Any]] = None
    question: Optional[str] = None
    answer: Optional[str] = None
    citations: Optional[List[Dict[str, Any]]] = []
    timestamp: Optional[str] = None
    
    # Phoenix trace correlation
    trace_id: Optional[str] = None

class FeedbackResponse(BaseModel):
    """Feedback submission response model"""
    message: str
    status: str  # "success" or "error"

def submit_span_annotation(span_id: str, feedback_data: dict, qa_id: str = None) -> bool:
    """
    Submit feedback as a span annotation to Phoenix using their span annotations API.
    
    Formats the span ID as a 16-character lowercase hexadecimal string as required by Phoenix.
    """

    import os
    import time
    import uuid
    import httpx
    import json
    import logging
    from time import sleep

    logger = logging.getLogger(__name__)
    
    # Cannot annotate without a span_id
    if not span_id:
        logger.error("Cannot submit annotation without a valid span_id")
        return False
        
    # Convert span_id to the required 16-character lowercase hexadecimal format
    try:
        # First, try to convert the span_id to an integer if it's a string
        span_id_int = int(span_id) if isinstance(span_id, str) else span_id
        
        # Convert to 16-character lowercase hexadecimal string - this is the format required by Phoenix
        formatted_span_id = format(span_id_int, '016x')
        
        logger.info(f"Original span ID: {span_id} (decimal)")
        logger.info(f"Converted to required 16-character hex format: {formatted_span_id}")
    except (ValueError, TypeError) as e:
        logger.warning(f"Failed to convert span_id to hex: {e}. Using original format.")
        formatted_span_id = str(span_id)
    
    logger.info(f"Attempting to annotate span with ID: {formatted_span_id}")
    
    phoenix_endpoint = os.getenv('PHOENIX_COLLECTOR_ENDPOINT', 'https://app.phoenix.arize.com')
    # Use synchronous processing to get immediate feedback
    annotation_endpoint = f"{phoenix_endpoint}/v1/span_annotations?sync=true"
    
    def get_phoenix_headers():
        client_headers = os.getenv('PHOENIX_CLIENT_HEADERS')
        headers = {"Content-Type": "application/json"}
        
        # Try the direct Phoenix API key approach first
        phoenix_api_key = os.getenv('PHOENIX_API_KEY')
        if phoenix_api_key:
            # Remove 'api_key=' prefix if present
            if phoenix_api_key.startswith('api_key='):
                phoenix_api_key = phoenix_api_key[8:]
            headers['api_key'] = phoenix_api_key
            logger.info("Using explicit PHOENIX_API_KEY")
            return headers
        
        # For Arize Cloud, use PHOENIX_CLIENT_HEADERS (contains api_key)
        if client_headers:
            try:
                # Check if client_headers starts with 'api_key='
                if client_headers.startswith('api_key='):
                    # Extract the actual key (remove 'api_key=' prefix)
                    api_key_value = client_headers[8:]
                    headers['api_key'] = api_key_value
                    logger.info("Using api_key value from PHOENIX_CLIENT_HEADERS (removed prefix)")
                    return headers
                    
                # Check if it's in key:value format (like '71c89f6ab6b6dafbb51:a61f175')
                if ':' in client_headers and not client_headers.startswith('{'):
                    headers['api_key'] = client_headers
                    logger.info("Using api_key directly from PHOENIX_CLIENT_HEADERS")
                    return headers
                    
                # Or it might be JSON formatted
                import json
                headers_dict = json.loads(client_headers)
                if 'api_key' in headers_dict:
                    headers['api_key'] = headers_dict['api_key']
                    logger.info("Using api_key from PHOENIX_CLIENT_HEADERS JSON")
                    return headers
            except json.JSONDecodeError:
                # Not JSON, likely a direct api_key
                headers['api_key'] = client_headers
                logger.info("Using PHOENIX_CLIENT_HEADERS as direct api_key")
                return headers
            except Exception as e:
                logger.error(f"Error processing PHOENIX_CLIENT_HEADERS: {e}")
        
        logger.warning("No Phoenix API key found - annotation may fail")
        return headers

    # Get authentication headers
    headers = get_phoenix_headers()
    
    # Generate a unique annotation ID based on qa_id and timestamp
    annotation_id = f"feedback_{qa_id}_{int(time.time())}" if qa_id else f"feedback_{uuid.uuid4()}_{int(time.time())}"
    
    # Prepare annotation data list with the formatted span ID
    annotation_data = []
    
    # Add user comment annotation if present
    if feedback_data.get("feedback_text"):
        annotation_data.append({
            "id": f"{annotation_id}_user_comment",
            "name": "User Comment",  # Required field by Phoenix API
            "span_id": formatted_span_id,
            "label": "user_feedback",
            "score": None,
            "explanation": feedback_data.get("feedback_text"),
            "annotator_kind": "HUMAN",  # Required field by Phoenix API
            # Keep qa_id as custom metadata
            "metadata": {"qa_id": qa_id} if qa_id else {}
        })
    
    # Add answer/relevance rating annotation
    if "relevance" in feedback_data:
        annotation_data.append({
            "id": f"{annotation_id}_relevance",
            "name": "Relevance Rating",  # Required field by Phoenix API
            "span_id": formatted_span_id,
            "label": "relevance",
            "score": feedback_data["relevance"],
            "explanation": None,
            "annotator_kind": "HUMAN",  # Required field by Phoenix API
            # Keep qa_id as custom metadata
            "metadata": {"qa_id": qa_id} if qa_id else {}
        })
    
    # Add factual accuracy annotation
    if "factual_accuracy" in feedback_data:
        annotation_data.append({
            "id": f"{annotation_id}_factual",
            "name": "Factual Accuracy",  # Required field by Phoenix API
            "span_id": formatted_span_id,
            "label": "factual_accuracy",
            "score": int(bool(feedback_data["factual_accuracy"])),
            "explanation": None,
            "annotator_kind": "HUMAN",  # Required field by Phoenix API
            # Keep qa_id as custom metadata
            "metadata": {"qa_id": qa_id} if qa_id else {}
        })
    
    # Skip if no annotation data was created
    if not annotation_data:
        logger.warning(f"No annotation data created for feedback: {feedback_data}")
        return False
    
    # Prepare the payload
    payload = {
        "data": annotation_data
    }
    
    # Convert to JSON for logging and sending
    payload_json = json.dumps(payload)
    logger.info(f"Submitting annotation to Phoenix at {annotation_endpoint}")
    logger.info(f"Annotation payload: {payload_json}")
    logger.info(f"Headers being used: {headers}")
    
    # Submit the annotation
    try:
        response = httpx.post(
            annotation_endpoint,
            headers=headers,
            json=payload,
            timeout=30.0  # Use a longer timeout
        )
        
        if response.status_code == 200:
            logger.info(f"Successfully submitted annotation for span {span_id}")
            return True
        else:
            logger.error(f"Failed to submit annotation: {response.status_code} - {response.text}")
            logger.error(f"Headers used: {headers}")
            logger.error(f"Full annotation payload: {payload_json}")
            return False
    except Exception as e:
        logger.error(f"Exception submitting annotation: {e}", exc_info=True)
        logger.error(f"Attempted endpoint: {annotation_endpoint}")
        logger.error(f"Headers: {headers}")
        return False

def associate_feedback_with_spans(session_id: str, qa_id: str, feedback_data: Dict[str, Any]) -> bool:
    """
    Attach feedback as an annotation to the correct Phoenix span using the native API and the span registry (Redis or in-memory).
    Returns True if successful, False otherwise.
    """
    import logging
    logger = logging.getLogger(__name__)
    try:
        # Look up the span_id using the registry (handles Redis or in-memory)
        from .spans import find_qa_span_id
        target_span_id = find_qa_span_id(session_id, qa_id)
        if not target_span_id:
            logger.error(f"No span ID found for session {session_id}, qa_id {qa_id}")
            return False
            
        # Log the span ID we found for debugging
        logger.info(f"Found target span ID: {target_span_id} for session={session_id}, qa_id={qa_id}")
            
        # Submit annotation to Phoenix
        success = submit_span_annotation(target_span_id, feedback_data, qa_id)
        if success:
            logger.info(f"Feedback annotation submitted for session {session_id}, qa_id {qa_id}")
            return True
        else:
            logger.error(f"Failed to submit feedback annotation for session {session_id}, qa_id {qa_id}")
            return False
    except Exception as e:
        logger.error(f"Failed to associate feedback with spans: {e}", exc_info=True)
        return False
