"""
Phoenix Native Feedback System for ATLAS

This module implements the correct Phoenix Arize approach for associating
feedback with spans using Phoenix's native span evaluation system.
"""

import logging
import json
import asyncio
from pydantic import BaseModel, ConfigDict
from typing import Optional, List, Dict, Any
from .spans import find_qa_span_id
from datetime import datetime

logger = logging.getLogger(__name__)

async def find_qa_span_id_with_retry(session_id: str, qa_id: str, max_retries: int = 3) -> Optional[str]:
    """
    Find span ID with retry logic for development SQLite timing issues.
    In production (Redis), this will succeed on first attempt with minimal overhead.
    """
    delays = [0.05, 0.1, 0.2]  # 50ms, 100ms, 200ms
    
    for i in range(max_retries):
        span_id = find_qa_span_id(session_id, qa_id)
        if span_id:
            return span_id
        
        if i < max_retries - 1:  # Don't sleep on last attempt
            await asyncio.sleep(delays[min(i, len(delays)-1)])
    
    return None

class UserFeedback(BaseModel):
    """User feedback submission model"""
    model_config = ConfigDict(extra='ignore')
    
    session_id: str
    qa_id: str
    
    # Existing fields (for backward compatibility)
    relevance: Optional[int] = None
    factual_accuracy: Optional[int] = None  # Now accepts numeric ratings (1-5)
    corpus_fidelity: Optional[int] = None  # 1-5 Likert: groundedness in retrieved corpus
    source_quality: Optional[int] = None
    clarity: Optional[int] = None
    question_rating: Optional[int] = None
    user_category: Optional[str] = None
    user_type: Optional[str] = None  # 'expert' | 'non_expert'
    tags: Optional[List[str]] = []
    feedback_text: Optional[str] = None
    model_answer: Optional[str] = None
    
    # New inline feedback fields
    feedback_type: Optional[str] = None  # 'simple', 'extended', or 'ai_enhanced'
    sentiment: Optional[str] = None  # 'positive' or 'negative'
    
    # New extended feedback fields
    analysis_quality: Optional[int] = None  # 1-5 Likert scale
    difficulty: Optional[int] = None  # 1-5 Likert scale
    additional_comments: Optional[str] = None  # Free text field for additional user feedback
    
    # New faults structure (alternative to tags)
    faults: Optional[Dict[str, bool]] = None  # {hallucination, off_topic, inappropriate, bias}
    
    # Additional rich data from frontend
    test_target: Optional[Dict[str, Any]] = None
    question: Optional[str] = None
    answer: Optional[str] = None
    citations: Optional[List[Dict[str, Any]]] = []
    timestamp: Optional[str] = None
    
    # Phoenix trace correlation
    trace_id: Optional[str] = None
    
    # AI-Enhanced feedback fields (minimal addition)
    ai_validation: Optional[Dict[str, Any]] = None  # Full AI validation results
    ai_agreement: Optional[str] = None  # Agreement level with AI assessment  
    ratings: Optional[Dict[str, int]] = None  # Human ratings for AI-enhanced feedback

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

def get_corpus_fidelity_description(score: int) -> str:
    """Return a description for a corpus fidelity score (groundedness in the retrieved corpus)."""
    descriptions = {
        1: "1/5: Not grounded - Cites no sources or contradicts them",
        2: "2/5: Weak grounding - Sparse or weak support from sources",
        3: "3/5: Moderate grounding - Some support but gaps or overreach",
        4: "4/5: Strong grounding - Well supported by retrieved sources",
        5: "5/5: Excellent grounding - Directly supported and faithful to sources"
    }
    return descriptions.get(score, f"Corpus fidelity score: {score}/5")

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

def get_analysis_quality_description(score: int) -> str:
    """Return a description for analysis quality score"""
    descriptions = {
        1: "1/5: Poor analysis - Lacks depth or accuracy",
        2: "2/5: Fair analysis - Basic understanding shown",
        3: "3/5: Good analysis - Adequate historical reasoning",
        4: "4/5: Very good analysis - Strong historical insight",
        5: "5/5: Excellent analysis - Outstanding historical scholarship"
    }
    return descriptions.get(score, f"Analysis quality score: {score}/5")

def get_difficulty_description(score: int) -> str:
    """Return a description for query difficulty score"""
    descriptions = {
        1: "1/5: Very easy - Basic factual query",
        2: "2/5: Easy - Simple research question",
        3: "3/5: Moderate - Requires some analysis",
        4: "4/5: Difficult - Complex research question",
        5: "5/5: Very difficult - Highly complex query requiring deep expertise"
    }
    return descriptions.get(score, f"Query difficulty score: {score}/5")

def get_sentiment_description(sentiment: str) -> str:
    """Return a description for sentiment feedback"""
    descriptions = {
        "positive": "👍 Positive - User found response helpful",
        "negative": "👎 Negative - User found response unhelpful"
    }
    return descriptions.get(sentiment, f"Sentiment: {sentiment}")

def format_faults_list(faults: Dict[str, bool]) -> List[str]:
    """Convert faults dictionary to list of active fault types"""
    if not faults:
        return []
    return [fault_type for fault_type, is_present in faults.items() if is_present]

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
        
    except (ValueError, TypeError) as e:
        logger.warning(f"Failed to convert span_id to hex: {e}. Using original format.")
        formatted_span_id = str(span_id)
    
    
    phoenix_endpoint = os.getenv('PHOENIX_COLLECTOR_ENDPOINT', 'https://app.phoenix.arize.com')
    # Use synchronous processing to get immediate feedback. For POST, use non-project path.
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
            return headers
        
        # For Arize Cloud, use PHOENIX_CLIENT_HEADERS (contains api_key)
        if client_headers:
            try:
                # Check if client_headers starts with 'api_key='
                if client_headers.startswith('api_key='):
                    # Extract the actual key (remove 'api_key=' prefix)
                    api_key_value = client_headers[8:]
                    headers['api_key'] = api_key_value
                    return headers
                    
                # Check if it's in key:value format (like '71c89f6ab6b6dafbb51:a61f175')
                if ':' in client_headers and not client_headers.startswith('{'):
                    headers['api_key'] = client_headers
                    return headers
                    
                # Or it might be JSON formatted
                import json
                headers_dict = json.loads(client_headers)
                if 'api_key' in headers_dict:
                    headers['api_key'] = headers_dict['api_key']
                    return headers
            except json.JSONDecodeError:
                # Not JSON, likely a direct api_key
                headers['api_key'] = client_headers
                return headers
            except Exception as e:
                logger.error(f"Error processing PHOENIX_CLIENT_HEADERS: {e}")
        
        logger.warning("No Phoenix API key found - annotation may fail")
        return headers

    # Get authentication headers
    headers = get_phoenix_headers()
    
    # Generate a unique annotation ID based on qa_id and timestamp
    # Check if this is inter-rater feedback by looking for inter-rater specific fields
    is_inter_rater = (
        feedback_data.get('is_inter_rater') is True and 
        feedback_data.get('original_span_id') and 
        feedback_data.get('rater_id')
    )
    
    timestamp = int(time.time())

    # Determine inter-rater number FIRST if this is inter-rater feedback
    inter_rater_number = None
    if is_inter_rater:
        try:
            # Query existing inter-rater count for the original span
            from backend.services.phoenix_client import phoenix_client
            original_span_id = feedback_data.get('original_span_id')

            # Get count asynchronously - need to handle sync context
            import asyncio
            try:
                # Try to get existing event loop
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # We're in an async context already - this shouldn't happen in submit_span_annotation
                    # but handle it gracefully
                    logger.warning("Cannot query inter-rater count in running event loop - using fallback")
                    inter_rater_number = None
                else:
                    # Run the async function in the loop
                    count = loop.run_until_complete(phoenix_client.get_inter_rater_count(original_span_id))
                    inter_rater_number = count + 1
            except RuntimeError:
                # No event loop exists, create one
                count = asyncio.run(phoenix_client.get_inter_rater_count(original_span_id))
                inter_rater_number = count + 1

            logger.info(f"Inter-rater number determined: {inter_rater_number}")
        except Exception as e:
            logger.warning(f"Failed to determine inter-rater number: {e}. Using fallback format.")
            inter_rater_number = None

    # Generate annotation ID - include inter_rater_number for uniqueness
    if is_inter_rater:
        # Use inter-rater specific annotation ID format with number for uniqueness
        rater_id = feedback_data.get('rater_id', f"rater_{timestamp}")[:8]  # First 8 chars for brevity
        number_suffix = f"_{inter_rater_number}" if inter_rater_number else ""
        annotation_id = f"inter_rater_{rater_id}{number_suffix}_{qa_id}_{timestamp}" if qa_id else f"inter_rater_{rater_id}{number_suffix}_{uuid.uuid4()}_{timestamp}"
    else:
        # Regular feedback annotation ID
        annotation_id = f"feedback_{qa_id}_{timestamp}" if qa_id else f"feedback_{uuid.uuid4()}_{timestamp}"

    # Prepare annotation data list with the formatted span ID
    annotation_data = []
    
    # Helper function to create appropriate metadata
    def get_annotation_metadata():
        metadata = {"qa_id": qa_id} if qa_id else {}
        
        if is_inter_rater:
            # Add inter-rater specific metadata
            metadata.update({
                "is_inter_rater": True,
                "feedback_type": "inter_rater",
                "original_span_id": feedback_data.get("original_span_id"),
                "rater_id": feedback_data.get("rater_id"),
                "inter_rater_number": inter_rater_number,
                "inter_rater_timestamp": datetime.now().isoformat()
            })
        else:
            # Regular feedback metadata
            metadata["feedback_type"] = "original"
            # Attach anonymized original user id when present
            if feedback_data.get("user_id"):
                metadata["user_id"] = feedback_data["user_id"]
        
        return metadata
    
    # Helper function to get annotation name prefix
    def get_annotation_name(base_name: str, inter_rater_number: Optional[int] = None) -> str:
        if is_inter_rater and inter_rater_number is not None:
            return f"[inter-rating-{inter_rater_number}] {base_name}"
        elif is_inter_rater:
            # Fallback to generic prefix if number not available
            return f"[Inter-rater] {base_name}"
        else:
            return base_name
    
    # Add user comment annotation if present
    if feedback_data.get("feedback_text"):
        annotation_data.append({
            "id": f"{annotation_id}_user_comment",
            "name": get_annotation_name("User Comment", inter_rater_number),  # Required field by Phoenix API
            "span_id": formatted_span_id,
            "annotator_kind": "HUMAN",  # Required field by Phoenix API
            "result": {  # Nest these fields inside result as expected by Phoenix
                "label": "user_feedback",
                "score": None,
                "explanation": feedback_data.get("feedback_text")
            },
            "metadata": get_annotation_metadata()
        })
    
    # Add answer/relevance rating annotation
    if "relevance" in feedback_data and feedback_data["relevance"] is not None:
        annotation_data.append({
            "id": f"{annotation_id}_relevance",
            "name": get_annotation_name("Relevance Rating", inter_rater_number),  # Required field by Phoenix API
            "span_id": formatted_span_id,
            "annotator_kind": "HUMAN",  # Required field by Phoenix API
            "result": {  # Nest these fields inside result as expected by Phoenix
                "label": "relevance",
                "score": feedback_data["relevance"],
                "explanation": get_relevance_description(feedback_data['relevance'])  # Add explanation for Phoenix UI
            },
            "metadata": get_annotation_metadata()
        })
    
    # Add factual accuracy annotation
    if "factual_accuracy" in feedback_data and feedback_data["factual_accuracy"] is not None:
        accuracy_value = feedback_data["factual_accuracy"]
        
        # Use the actual numeric rating (1-5 Likert scale)
        score = accuracy_value
        if accuracy_value <= 2:
            explanation = f"Low factual accuracy (rated {accuracy_value}/5)"
        elif accuracy_value == 3:
            explanation = f"Moderate factual accuracy (rated {accuracy_value}/5)"
        else:
            explanation = f"High factual accuracy (rated {accuracy_value}/5)"
            
        annotation_data.append({
            "id": f"{annotation_id}_factual",
            "name": get_annotation_name("Factual Accuracy", inter_rater_number),  # Required field by Phoenix API
            "span_id": formatted_span_id,
            "annotator_kind": "HUMAN",  # Required field by Phoenix API
            "result": {  # Nest these fields inside result as expected by Phoenix
                "label": "factual_accuracy",
                "score": score,
                "explanation": explanation  # Add explanation for Phoenix UI
            },
            "metadata": get_annotation_metadata()
        })
    
    # Add corpus fidelity annotation (new)
    if "corpus_fidelity" in feedback_data and feedback_data["corpus_fidelity"] is not None:
        fidelity_score = feedback_data["corpus_fidelity"]
        annotation_data.append({
            "id": f"{annotation_id}_corpus_fidelity",
            "name": get_annotation_name("Corpus Fidelity", inter_rater_number),
            "span_id": formatted_span_id,
            "annotator_kind": "HUMAN",
            "result": {
                "label": "corpus_fidelity",
                "score": fidelity_score,
                "explanation": get_corpus_fidelity_description(fidelity_score)
            },
            "metadata": get_annotation_metadata()
        })
    
    # Add clarity rating annotation if present
    if "clarity" in feedback_data and feedback_data["clarity"] is not None:
        clarity_score = feedback_data["clarity"]
        annotation_data.append({
            "id": f"{annotation_id}_clarity",
            "name": get_annotation_name("Clarity", inter_rater_number),  # Required field by Phoenix API
            "span_id": formatted_span_id,
            "annotator_kind": "HUMAN",  # Required field by Phoenix API
            "result": {  # Nest these fields inside result as expected by Phoenix
                "label": "clarity",
                "score": clarity_score,
                "explanation": get_clarity_description(clarity_score)  # Add detailed explanation for Phoenix UI
            },
            "metadata": get_annotation_metadata()
        })
        
    # Add source quality rating annotation if present
    if "source_quality" in feedback_data and feedback_data["source_quality"] is not None:
        source_quality_score = feedback_data["source_quality"]
        annotation_data.append({
            "id": f"{annotation_id}_source_quality",
            "name": get_annotation_name("Source Quality", inter_rater_number),  # Required field by Phoenix API
            "span_id": formatted_span_id,
            "annotator_kind": "HUMAN",  # Required field by Phoenix API
            "result": {  # Nest these fields inside result as expected by Phoenix
                "label": "source_quality",
                "score": source_quality_score,
                "explanation": get_source_quality_description(source_quality_score)  # Add detailed explanation for Phoenix UI
            },
            "metadata": get_annotation_metadata()
        })
        
    # Add question rating annotation if present
    if "question_rating" in feedback_data and feedback_data["question_rating"] is not None:
        question_rating_score = feedback_data["question_rating"]
        annotation_data.append({
            "id": f"{annotation_id}_question_rating",
            "name": get_annotation_name("Question Difficulty", inter_rater_number),  # Required field by Phoenix API
            "span_id": formatted_span_id,
            "annotator_kind": "HUMAN",  # Required field by Phoenix API
            "result": {  # Nest these fields inside result as expected by Phoenix
                "label": "question_difficulty",
                "score": question_rating_score,
                "explanation": get_question_rating_description(question_rating_score)  # Add detailed explanation for Phoenix UI
            },
            "metadata": get_annotation_metadata()
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
            "name": get_annotation_name("User Category", inter_rater_number),  # Required field by Phoenix API
            "span_id": formatted_span_id,
            "annotator_kind": "HUMAN",  # Required field by Phoenix API
            "result": {  # Nest these fields inside result as expected by Phoenix
                "label": "user_category",
                "score": category_score,  # Use numeric score for Phoenix compatibility
                "explanation": get_user_category_description(user_category)  # Add detailed explanation for Phoenix UI
            },
            "metadata": {"qa_id": qa_id, "user_category": user_category} if qa_id else {"user_category": user_category}
        })

    # Add user type annotation if present (expert vs non_expert)  
    if "user_type" in feedback_data and feedback_data["user_type"]:
        user_type = feedback_data["user_type"]
        
        # Assign numeric scores to user types for Phoenix compatibility
        type_scores = {
            "expert": 2,
            "non_expert": 1
        }
        type_score = type_scores.get(user_type, 1)  # Default to 1 (non_expert)
        
        annotation_data.append({
            "id": f"{annotation_id}_user_type",
            "name": get_annotation_name("User Type", inter_rater_number),
            "span_id": formatted_span_id,
            "annotator_kind": "HUMAN",
            "result": {
                "label": "user_type", 
                "score": type_score,
                "explanation": f"User identified as: {user_type}"
            },
            "metadata": {"qa_id": qa_id, "user_type": user_type} if qa_id else {"user_type": user_type}
        })
    
    # Add tags as separate annotations if present
    if "tags" in feedback_data and feedback_data["tags"]:
        for i, tag in enumerate(feedback_data["tags"]):
            annotation_data.append({
                "id": f"{annotation_id}_tag_{i}",
                "name": get_annotation_name(f"Tag: {tag}", inter_rater_number),  # Make the tag name visible
                "span_id": formatted_span_id,
                "annotator_kind": "HUMAN",  # Required field by Phoenix API
                "result": {  # Nest these fields inside result as expected by Phoenix
                    "label": "feedback_tag",
                    "score": 1,  # Binary presence of tag
                    "explanation": f"User tagged response as: {tag}"
                },
                "metadata": {"qa_id": qa_id, "tag": tag} if qa_id else {"tag": tag}
            })
    
    # Add new inline feedback fields
    
    # Add thumbs up/down annotation if present (following Phoenix docs)
    if "sentiment" in feedback_data and feedback_data["sentiment"]:
        if feedback_data["sentiment"] == "positive":
            label = "thumbs-up"
            score = 1
        elif feedback_data["sentiment"] == "negative":
            label = "thumbs-down"
            score = 0
        else:
            # Skip unknown sentiment values
            label = None
            score = None
            
        if label and score is not None:
            annotation_data.append({
                "id": f"{annotation_id}_user_feedback",
                "name": "user feedback",  # Phoenix standard name
                "span_id": formatted_span_id,
                "annotator_kind": "HUMAN",
                "result": {
                    "label": label,  # "thumbs-up" or "thumbs-down"
                    "score": score   # 1 for thumbs-up, 0 for thumbs-down
                },
                "metadata": {"qa_id": qa_id, "sentiment": feedback_data["sentiment"]} if qa_id else {"sentiment": feedback_data["sentiment"]}
            })
    
    # Add analysis quality annotation if present
    if "analysis_quality" in feedback_data and feedback_data["analysis_quality"] is not None:
        analysis_quality_score = feedback_data["analysis_quality"]
        annotation_data.append({
            "id": f"{annotation_id}_analysis_quality",
            "name": get_annotation_name("Analysis Quality", inter_rater_number),
            "span_id": formatted_span_id,
            "annotator_kind": "HUMAN",
            "result": {
                "label": "analysis_quality",
                "score": analysis_quality_score,
                "explanation": get_analysis_quality_description(analysis_quality_score)
            },
            "metadata": get_annotation_metadata()
        })
    
    # Add difficulty annotation if present
    if "difficulty" in feedback_data and feedback_data["difficulty"] is not None:
        difficulty_score = feedback_data["difficulty"]
        annotation_data.append({
            "id": f"{annotation_id}_difficulty",
            "name": get_annotation_name("Query Difficulty", inter_rater_number),
            "span_id": formatted_span_id,
            "annotator_kind": "HUMAN",
            "result": {
                "label": "query_difficulty",
                "score": difficulty_score,
                "explanation": get_difficulty_description(difficulty_score)
            },
            "metadata": get_annotation_metadata()
        })
    
    # Add faults annotations if present
    if "faults" in feedback_data and feedback_data["faults"]:
        active_faults = format_faults_list(feedback_data["faults"])
        for fault_type in active_faults:
            annotation_data.append({
                "id": f"{annotation_id}_fault_{fault_type}",
                "name": get_annotation_name(f"Fault: {fault_type.replace('_', ' ').title()}", inter_rater_number),
                "span_id": formatted_span_id,
                "annotator_kind": "HUMAN",
                "result": {
                    "label": "fault",
                    "score": 1,  # Binary presence of fault
                    "explanation": f"User identified fault: {fault_type.replace('_', ' ')}"
                },
                "metadata": {"qa_id": qa_id, "fault_type": fault_type} if qa_id else {"fault_type": fault_type}
            })
    
    # Add additional comments annotation if present (for Extended feedback)
    if "additional_comments" in feedback_data and feedback_data["additional_comments"]:
        annotation_data.append({
            "id": f"{annotation_id}_additional_comments",
            "name": get_annotation_name("Additional Comments", inter_rater_number),
            "span_id": formatted_span_id,
            "annotator_kind": "HUMAN",
            "result": {
                "label": "additional_feedback",
                "score": None,
                "explanation": feedback_data["additional_comments"]
            },
            "metadata": {"qa_id": qa_id, "feedback_type": "extended"} if qa_id else {"feedback_type": "extended"}
        })
    
    # Note: We don't need to add feedback_text here as it's already handled above as user_comment
    
    # Add AI-Enhanced feedback annotations (minimal addition - only if feedback_type is ai_enhanced)
    if feedback_data.get('feedback_type') == 'ai_enhanced':
        # Add AI validation results as separate annotations
        if "ai_validation" in feedback_data and feedback_data["ai_validation"]:
            ai_validation = feedback_data["ai_validation"]
            
            # Add AI overall quality assessment
            structured_feedback = ai_validation.get("structured_feedback")
            if structured_feedback and structured_feedback.get("overall_quality"):
                overall_quality = structured_feedback["overall_quality"]
                quality_scores = {"excellent": 5, "good": 4, "fair": 3, "poor": 2}
                quality_score = quality_scores.get(overall_quality, 3)
                
                annotation_data.append({
                    "id": f"{annotation_id}_ai_overall_quality",
                    "name": "AI Overall Quality Assessment",
                    "span_id": formatted_span_id,
                    "annotator_kind": "LLM",  # AI assessment
                    "result": {
                        "label": "ai_overall_quality",
                        "score": quality_score,
                        "explanation": f"AI assessed overall quality as: {overall_quality}"
                    },
                    "metadata": {
                        "qa_id": qa_id,
                        "feedback_type": "ai_validation"
                    } if qa_id else {"feedback_type": "ai_validation"}
                })
            
            # Add AI individual category scores
            if structured_feedback:
                ai_categories = ['factual_accuracy', 'completeness', 'relevance', 'citation_quality', 'clarity', 'historical_context']
                for category in ai_categories:
                    if category in structured_feedback and isinstance(structured_feedback[category], dict):
                        category_data = structured_feedback[category]
                        if 'score' in category_data:
                            annotation_data.append({
                                "id": f"{annotation_id}_ai_{category}",
                                "name": f"AI {category.replace('_', ' ').title()}",
                                "span_id": formatted_span_id,
                                "annotator_kind": "LLM",  # AI assessment
                                "result": {
                                    "label": f"ai_{category}",
                                    "score": category_data['score'],
                                    "explanation": f"AI {category.replace('_', ' ')} assessment: {category_data['score']}/5"
                                },
                                "metadata": {
                                    "qa_id": qa_id,
                                    "feedback_type": "ai_validation",
                                    "category": category
                                } if qa_id else {"feedback_type": "ai_validation", "category": category}
                            })
        
        # Add human ratings from AI-enhanced feedback
        if "ratings" in feedback_data and feedback_data["ratings"]:
            human_ratings = feedback_data["ratings"]
            for rating_type, rating_value in human_ratings.items():
                if rating_value is not None:
                    annotation_data.append({
                        "id": f"{annotation_id}_human_{rating_type}",
                        "name": f"Human {rating_type.replace('_', ' ').title()}",
                        "span_id": formatted_span_id,
                        "annotator_kind": "HUMAN",  # Human assessment
                        "result": {
                            "label": f"human_{rating_type}",
                            "score": rating_value,
                            "explanation": f"Human {rating_type.replace('_', ' ')} assessment: {rating_value}/5"
                        },
                        "metadata": {
                            "qa_id": qa_id,
                            "feedback_type": "ai_enhanced_human"
                        } if qa_id else {"feedback_type": "ai_enhanced_human"}
                    })
        
        # Add AI agreement level
        if "ai_agreement" in feedback_data and feedback_data["ai_agreement"]:
            agreement_scores = {
                "strongly_agree": 5, "agree": 4, "neutral": 3, "disagree": 2, "strongly_disagree": 1
            }
            agreement_score = agreement_scores.get(feedback_data["ai_agreement"], 3)
            
            annotation_data.append({
                "id": f"{annotation_id}_ai_agreement",
                "name": "AI Agreement Level",
                "span_id": formatted_span_id,
                "annotator_kind": "HUMAN",  # Human assessment of AI agreement
                "result": {
                    "label": "ai_agreement",
                    "score": agreement_score,
                    "explanation": f"Human agreement with AI assessment: {feedback_data['ai_agreement']}"
                },
                "metadata": {
                    "qa_id": qa_id,
                    "feedback_type": "ai_enhanced_human"
                } if qa_id else {"feedback_type": "ai_enhanced_human"}
            })
        
    # Add model answer if provided
    if "model_answer" in feedback_data and feedback_data["model_answer"]:
        annotation_data.append({
            "id": f"{annotation_id}_model_answer",
            "name": get_annotation_name("Model Answer", inter_rater_number),
            "span_id": formatted_span_id,
            "annotator_kind": "HUMAN",
            "result": {
                "label": "model_answer",
                "score": None,
                "explanation": feedback_data["model_answer"]
            },
            "metadata": get_annotation_metadata()
        })
    
    # Skip if no annotation data was created
    if not annotation_data:
        # Do not log raw feedback payload to avoid capturing PII
        logger.warning("No annotation data created for feedback (payload omitted)")
        return False
    
    # Prepare the payload
    payload = {
        "data": annotation_data
    }
    
    # Convert to JSON for logging and sending
    payload_json = json.dumps(payload)
    
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
            logger.error(f"Failed to submit annotation: {response.status_code}")
            return False
    except Exception as e:
        logger.error(f"Exception submitting annotation: {e}", exc_info=True)
        logger.error(f"Attempted endpoint: {annotation_endpoint}")
        return False

async def associate_feedback_with_spans(session_id: str, qa_id: str, feedback_data: Dict[str, Any]) -> bool:
    """
    Attach feedback as an annotation to the LLM generation response span using the native API and the span registry.
    This ensures feedback is directly associated with the model's response output.
    Returns True if successful, False otherwise.
    """
    import logging
    logger = logging.getLogger(__name__)
    try:
        # The LLM response span is registered with a special key format of {qa_id}_response
        # Look up this response span specifically for feedback with retry logic
        
        # Special key pattern used for the response span in llm.py
        response_key = f"{qa_id}_response"
        response_span_id = await find_qa_span_id_with_retry(session_id, response_key)
        
        if response_span_id:
            
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
            
            qa_span_id = await find_qa_span_id_with_retry(session_id, qa_id)
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
