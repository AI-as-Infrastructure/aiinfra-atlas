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
    factual_accuracy: Optional[str] = None  # Changed from bool to str to support "mixed"
    source_quality: Optional[int] = None
    clarity: Optional[int] = None
    question_rating: Optional[int] = None
    user_category: Optional[str] = None  # New field for user category
    tags: Optional[List[str]] = []
    feedback_text: Optional[str] = None
    model_answer: Optional[str] = None
    
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

def get_relevance_description(score: int) -> str:
    """Return a description for a relevance score"""
    descriptions = {
        1: "1/5: Not relevant - Answer doesn't address the question",
        2: "2/5: Somewhat relevant - Answer touches on the topic but misses key points",
        3: "3/5: Moderately relevant - Answer addresses main points but could be more focused",
        4: "4/5: Very relevant - Answer addresses the question well",
        5: "5/5: Perfectly relevant - Answer completely addresses the question"
    }
    return descriptions.get(score, f"Relevance score: {score}/5")

def get_clarity_description(score: int) -> str:
    """Return a description for a clarity score"""
    descriptions = {
        1: "1/5: Very unclear - Hard to understand the answer",
        2: "2/5: Somewhat unclear - Parts of the answer are confusing",
        3: "3/5: Moderately clear - Answer is understandable but could be clearer",
        4: "4/5: Very clear - Answer is easy to understand",
        5: "5/5: Perfectly clear - Answer is exceptionally well-explained"
    }
    return descriptions.get(score, f"Clarity score: {score}/5")

def get_source_quality_description(score: int) -> str:
    """Return a description for a source quality score"""
    descriptions = {
        1: "1/5: Poor sources - Unreliable or irrelevant",
        2: "2/5: Fair sources - Limited reliability or relevance",
        3: "3/5: Good sources - Adequate reliability and relevance",
        4: "4/5: Very good sources - Reliable and highly relevant",
        5: "5/5: Excellent sources - Authoritative and perfectly matched"
    }
    return descriptions.get(score, f"Source quality score: {score}/5")

def get_question_rating_description(score: int) -> str:
    """Return a description for a question difficulty/challenge rating score"""
    descriptions = {
        1: "1/5: Very easy - Straightforward question requiring minimal context",
        2: "2/5: Easy - Simple question with clear answer path",
        3: "3/5: Moderate - Requires some reasoning or specific knowledge",
        4: "4/5: Difficult - Complex question requiring deep analysis",
        5: "5/5: Very difficult - Highly challenging question for the LLM"
    }
    return descriptions.get(score, f"Question difficulty score: {score}/5")

def get_user_category_description(category: str) -> str:
    """Return a description for a user category"""
    descriptions = {
        "General User": "General User - Broad interest in the content",
        "Hansard Expert": "Hansard Expert - Specialist in parliamentary records and procedures",
        "Digital HASS Researcher": "Digital HASS Researcher - Humanities and Social Sciences researcher using digital methods", 
        "GLAM Practitioner": "GLAM Practitioner - Gallery, Library, Archive, or Museum professional"
    }
    return descriptions.get(category, f"User Category: {category}")

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
            "annotator_kind": "HUMAN",  # Required field by Phoenix API
            "result": {  # Nest these fields inside result as expected by Phoenix
                "label": "user_feedback",
                "score": None,
                "explanation": feedback_data.get("feedback_text")
            },
            # Include the question and answer if available
            "metadata": {
                "qa_id": qa_id,
                "question": feedback_data.get("question"),
                "answer": feedback_data.get("answer")
            } if qa_id else {}
        })
    
    # Add answer/relevance rating annotation
    if "relevance" in feedback_data:
        annotation_data.append({
            "id": f"{annotation_id}_relevance",
            "name": "Relevance Rating",  # Required field by Phoenix API
            "span_id": formatted_span_id,
            "annotator_kind": "HUMAN",  # Required field by Phoenix API
            "result": {  # Nest these fields inside result as expected by Phoenix
                "label": "relevance",
                "score": feedback_data["relevance"],
                "explanation": get_relevance_description(feedback_data['relevance'])  # Add explanation for Phoenix UI
            },
            "metadata": {"qa_id": qa_id} if qa_id else {}
        })
    
    # Add factual accuracy annotation
    if "factual_accuracy" in feedback_data:
        # Handle the three possible values: "true", "false", "mixed"
        accuracy_value = feedback_data["factual_accuracy"]
        
        if accuracy_value == "true":
            score = 1
            explanation = "Response is factually accurate"
        elif accuracy_value == "false":
            score = 0
            explanation = "Response contains factual errors"
        elif accuracy_value == "mixed":
            score = 0.5  # Use 0.5 to represent mixed accuracy
            explanation = "Response contains both accurate and inaccurate information"
        else:
            # Default case
            score = 0
            explanation = "Factual accuracy unclear"
            
        annotation_data.append({
            "id": f"{annotation_id}_factual",
            "name": "Factual Accuracy",  # Required field by Phoenix API
            "span_id": formatted_span_id,
            "annotator_kind": "HUMAN",  # Required field by Phoenix API
            "result": {  # Nest these fields inside result as expected by Phoenix
                "label": "factual_accuracy",
                "score": score,
                "explanation": explanation  # Add explanation for Phoenix UI
            },
            "metadata": {"qa_id": qa_id} if qa_id else {}
        })
    
    # Add clarity rating annotation if present
    if "clarity" in feedback_data:
        clarity_score = feedback_data["clarity"]
        annotation_data.append({
            "id": f"{annotation_id}_clarity",
            "name": "Clarity",  # Required field by Phoenix API
            "span_id": formatted_span_id,
            "annotator_kind": "HUMAN",  # Required field by Phoenix API
            "result": {  # Nest these fields inside result as expected by Phoenix
                "label": "clarity",
                "score": clarity_score,
                "explanation": get_clarity_description(clarity_score)  # Add detailed explanation for Phoenix UI
            },
            "metadata": {"qa_id": qa_id} if qa_id else {}
        })
        
    # Add source quality rating annotation if present
    if "source_quality" in feedback_data and feedback_data["source_quality"] is not None:
        source_quality_score = feedback_data["source_quality"]
        annotation_data.append({
            "id": f"{annotation_id}_source_quality",
            "name": "Source Quality",  # Required field by Phoenix API
            "span_id": formatted_span_id,
            "annotator_kind": "HUMAN",  # Required field by Phoenix API
            "result": {  # Nest these fields inside result as expected by Phoenix
                "label": "source_quality",
                "score": source_quality_score,
                "explanation": get_source_quality_description(source_quality_score)  # Add detailed explanation for Phoenix UI
            },
            "metadata": {"qa_id": qa_id} if qa_id else {}
        })
        
    # Add question rating annotation if present
    if "question_rating" in feedback_data and feedback_data["question_rating"] is not None:
        question_rating_score = feedback_data["question_rating"]
        annotation_data.append({
            "id": f"{annotation_id}_question_rating",
            "name": "Question Difficulty",  # Required field by Phoenix API
            "span_id": formatted_span_id,
            "annotator_kind": "HUMAN",  # Required field by Phoenix API
            "result": {  # Nest these fields inside result as expected by Phoenix
                "label": "question_difficulty",
                "score": question_rating_score,
                "explanation": get_question_rating_description(question_rating_score)  # Add detailed explanation for Phoenix UI
            },
            "metadata": {"qa_id": qa_id} if qa_id else {}
        })
        
    # Add user category annotation if present
    if "user_category" in feedback_data and feedback_data["user_category"]:
        user_category = feedback_data["user_category"]
        
        # Assign numeric scores to categories for Phoenix compatibility
        category_scores = {
            "General User": 1,
            "Hansard Expert": 2,
            "Digital HASS Researcher": 3,
            "GLAM Practitioner": 4
        }
        category_score = category_scores.get(user_category, 1)  # Default to 1
        
        annotation_data.append({
            "id": f"{annotation_id}_user_category",
            "name": "User Category",  # Required field by Phoenix API
            "span_id": formatted_span_id,
            "annotator_kind": "HUMAN",  # Required field by Phoenix API
            "result": {  # Nest these fields inside result as expected by Phoenix
                "label": "user_category",
                "score": category_score,  # Use numeric score for Phoenix compatibility
                "explanation": get_user_category_description(user_category)  # Add detailed explanation for Phoenix UI
            },
            "metadata": {"qa_id": qa_id, "user_category": user_category} if qa_id else {"user_category": user_category}
        })
    
    # Add tags as separate annotations if present
    if "tags" in feedback_data and feedback_data["tags"]:
        for i, tag in enumerate(feedback_data["tags"]):
            annotation_data.append({
                "id": f"{annotation_id}_tag_{i}",
                "name": f"Tag: {tag}",  # Make the tag name visible
                "span_id": formatted_span_id,
                "annotator_kind": "HUMAN",  # Required field by Phoenix API
                "result": {  # Nest these fields inside result as expected by Phoenix
                    "label": "feedback_tag",
                    "score": 1,  # Binary presence of tag
                    "explanation": f"User tagged response as: {tag}"
                },
                "metadata": {"qa_id": qa_id, "tag": tag} if qa_id else {"tag": tag}
            })
    
    # Note: We don't need to add feedback_text here as it's already handled above as user_comment
        
    # Add model answer if provided
    if "model_answer" in feedback_data and feedback_data["model_answer"]:
        annotation_data.append({
            "id": f"{annotation_id}_model_answer",
            "name": "Model Answer",
            "span_id": formatted_span_id,
            "annotator_kind": "HUMAN",
            "result": {
                "label": "model_answer",
                "score": None,
                "explanation": feedback_data["model_answer"]
            },
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
    Attach feedback as an annotation to the LLM generation response span using the native API and the span registry.
    This ensures feedback is directly associated with the model's response output.
    Returns True if successful, False otherwise.
    """
    import logging
    logger = logging.getLogger(__name__)
    try:
        # The LLM response span is registered with a special key format of {qa_id}_response
        # Look up this response span specifically for feedback
        from .spans import find_qa_span_id
        
        # Special key pattern used for the response span in llm.py
        response_key = f"{qa_id}_response"
        response_span_id = find_qa_span_id(session_id, response_key)
        
        if response_span_id:
            logger.info(f"Found response span ID: {response_span_id} for session={session_id}, qa_id={qa_id}")
            
            # Submit annotation to Phoenix using the response span
            success = submit_span_annotation(response_span_id, feedback_data, qa_id)
            if success:
                logger.info(f"Feedback annotation submitted to response span for session {session_id}, qa_id {qa_id}")
                return True
            else:
                logger.error(f"Failed to submit feedback annotation for session {session_id}, qa_id {qa_id}")
                return False
        else:
            # Fall back to the regular QA span if no response span is found
            logger.warning(f"No response span found for {response_key}, falling back to QA span")
            
            qa_span_id = find_qa_span_id(session_id, qa_id)
            if not qa_span_id:
                logger.error(f"No span ID found for session {session_id}, qa_id {qa_id}")
                return False
                
            # Submit annotation to Phoenix using the QA span as fallback
            success = submit_span_annotation(qa_span_id, feedback_data, qa_id)
            if success:
                logger.info(f"Feedback annotation submitted to QA span for session {session_id}, qa_id {qa_id}")
                return True
            else:
                logger.error(f"Failed to submit feedback annotation for session {session_id}, qa_id {qa_id}")
                return False
    except Exception as e:
        logger.error(f"Failed to associate feedback with spans: {e}", exc_info=True)
        return False
