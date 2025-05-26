"""
Phoenix Native Feedback System for ATLAS

This module implements the correct Phoenix Arize approach for associating
feedback with spans using Phoenix's native span evaluation system.
"""

import logging
from pydantic import BaseModel, ConfigDict
from typing import Optional, List, Dict, Any
from .spans import find_qa_span_id

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

class FeedbackResponse(BaseModel):
    """Feedback submission response model"""
    message: str
    status: str  # "success" or "error"

def associate_feedback_with_spans(session_id: str, qa_id: str, feedback_data: Dict[str, Any]) -> bool:
    """
    Associate feedback with spans using Phoenix's native span evaluation system.
    This is the correct Phoenix Arize approach for span-level feedback.
    """
    try:
        # Import Phoenix native components
        import phoenix as px
        from phoenix.trace import SpanEvaluations
        from phoenix.client import Client
        import pandas as pd
        
        # Find the original span ID
        span_id = find_qa_span_id(session_id, qa_id)
        if span_id is None:
            logger.warning(f"Could not find answer span for session_id={session_id}, qa_id={qa_id}")
            return False
        
        # Get Phoenix client for evaluation logging with proper configuration
        import os
        phoenix_endpoint = os.getenv("PHOENIX_COLLECTOR_ENDPOINT")
        phoenix_api_key = os.getenv("PHOENIX_API_KEY")
        
        if not phoenix_endpoint or not phoenix_api_key:
            logger.error("Phoenix configuration missing - PHOENIX_COLLECTOR_ENDPOINT and PHOENIX_API_KEY required")
            return False
        
        # Initialize Phoenix client for online service using the new API
        client = Client(
            base_url=phoenix_endpoint,
            headers={"api_key": phoenix_api_key}
        )
        
        # Create evaluation records for Phoenix native logging
        evaluations = []
        
        # Add structured evaluations using Phoenix's evaluation format
        if feedback_data.get("relevance") is not None:
            evaluations.append({
                "span_id": str(span_id),
                "label": "user_feedback",
                "score": feedback_data["relevance"],
                "explanation": f"User rated relevance as {feedback_data['relevance']}/5"
            })
        
        if feedback_data.get("factual_accuracy") is not None:
            evaluations.append({
                "span_id": str(span_id),
                "label": "user_feedback",
                "score": 1.0 if feedback_data["factual_accuracy"] else 0.0,
                "explanation": f"User marked as {'factually accurate' if feedback_data['factual_accuracy'] else 'factually inaccurate'}"
            })
        
        if feedback_data.get("source_quality") is not None:
            evaluations.append({
                "span_id": str(span_id),
                "label": "user_feedback",
                "score": feedback_data["source_quality"],
                "explanation": f"User rated source quality as {feedback_data['source_quality']}/5"
            })
        
        if feedback_data.get("clarity") is not None:
            evaluations.append({
                "span_id": str(span_id),
                "label": "user_feedback", 
                "score": feedback_data["clarity"],
                "explanation": f"User rated clarity as {feedback_data['clarity']}/5"
            })
        
        # Apply tags as evaluations
        if feedback_data.get("tags"):
            for tag in feedback_data["tags"]:
                evaluations.append({
                    "span_id": str(span_id),
                    "label": "user_tag",
                    "score": 1.0,
                    "explanation": f"User tagged response as '{tag}'"
                })
        
        # Add feedback text as an evaluation
        if feedback_data.get("feedback_text"):
            evaluations.append({
                "span_id": str(span_id),
                "label": "user_feedback",
                "score": None,  # Text feedback doesn't have a score
                "explanation": feedback_data["feedback_text"]
            })
        
        # Log evaluations to Phoenix using the correct API
        if evaluations:
            try:
                # Create DataFrame with correct schema for Phoenix
                eval_df = pd.DataFrame(evaluations)
                
                # Use SpanEvaluations class as required by Phoenix 3.25.0
                span_evaluations = SpanEvaluations(
                    dataframe=eval_df,
                    eval_name="User Feedback"
                )
                
                # Log evaluations using Phoenix client
                client.log_evaluations(span_evaluations)
                logger.info(f"Successfully logged Phoenix native evaluations for span {span_id} (session_id={session_id}, qa_id={qa_id})")
                return True
            except Exception as eval_error:
                if "401" in str(eval_error) or "Unauthorized" in str(eval_error):
                    logger.error(f"Phoenix authentication failed - check PHOENIX_API_KEY: {eval_error}")
                    logger.error("Ensure PHOENIX_API_KEY is set to: YOUR_API_KEY")
                else:
                    logger.error(f"Phoenix native feedback logging failed: {eval_error}")
                
                # Don't fall back - let the failure be visible
                logger.error("Phoenix feedback logging failed - no fallback used to ensure visibility of issues")
                return False
        else:
            logger.warning(f"No evaluation data to record for session_id={session_id}, qa_id={qa_id}")
            return False
        
    except ImportError:
        logger.error("Phoenix not available - feedback logging disabled")
        return False
    except Exception as e:
        logger.error(f"Error applying Phoenix native feedback: {e}", exc_info=True)
        return False