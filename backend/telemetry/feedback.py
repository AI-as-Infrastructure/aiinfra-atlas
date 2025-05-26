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

class FeedbackResponse(BaseModel):
    """Feedback submission response model"""
    message: str
    status: str  # "success" or "error"

def associate_feedback_with_spans(session_id: str, qa_id: str, feedback_data: Dict[str, Any]) -> bool:
    """
    Associate feedback with spans by adding evaluation attributes directly to existing spans.
    This creates annotations on the original spans rather than separate evaluation spans.
    """
    try:
        from opentelemetry import trace
        import json
        
        # Find span IDs - try multiple patterns
        response_span_id = find_qa_span_id(session_id, f"{qa_id}_response")
        qa_span_id = find_qa_span_id(session_id, qa_id)
        
        # Use any available span
        primary_span_id = response_span_id or qa_span_id
        
        if primary_span_id is None:
            logger.error(f"No spans found for feedback: session_id={session_id}, qa_id={qa_id}")
            # Log what spans we do have
            from .spans import _span_registry
            available_spans = _span_registry.get(session_id, {})
            logger.error(f"Available spans: {list(available_spans.keys())}")
            return False
        
        logger.info(f"Adding feedback annotations to span: {primary_span_id}")
        
        # Create evaluation attributes for the span
        evaluation_attributes = {}
        
        # Add Phoenix-style evaluation attributes
        if feedback_data.get("relevance") is not None:
            evaluation_attributes["evals.relevance.score"] = float(feedback_data["relevance"]) / 5.0
            evaluation_attributes["evals.relevance.label"] = "relevance"
            evaluation_attributes["evals.relevance.explanation"] = f"User rated relevance: {feedback_data['relevance']}/5"
        
        if feedback_data.get("factual_accuracy") is not None:
            evaluation_attributes["evals.factual_accuracy.score"] = 1.0 if feedback_data["factual_accuracy"] else 0.0
            evaluation_attributes["evals.factual_accuracy.label"] = "factual_accuracy"
            evaluation_attributes["evals.factual_accuracy.explanation"] = f"Factually accurate: {feedback_data['factual_accuracy']}"
        
        if feedback_data.get("clarity") is not None:
            evaluation_attributes["evals.clarity.score"] = float(feedback_data["clarity"]) / 5.0
            evaluation_attributes["evals.clarity.label"] = "clarity"
            evaluation_attributes["evals.clarity.explanation"] = f"User rated clarity: {feedback_data['clarity']}/5"
        
        if feedback_data.get("source_quality") is not None:
            evaluation_attributes["evals.source_quality.score"] = float(feedback_data["source_quality"]) / 5.0
            evaluation_attributes["evals.source_quality.label"] = "source_quality"
            evaluation_attributes["evals.source_quality.explanation"] = f"User rated source quality: {feedback_data['source_quality']}/5"
        
        if feedback_data.get("feedback_text"):
            evaluation_attributes["evals.user_comment.label"] = "user_comment"
            evaluation_attributes["evals.user_comment.explanation"] = feedback_data["feedback_text"]
        
        if not evaluation_attributes:
            logger.warning(f"No feedback data to log for {qa_id}")
            return False
        
        # Add summary attributes
        evaluation_attributes["user_feedback.submitted"] = True
        evaluation_attributes["user_feedback.timestamp"] = datetime.now().isoformat()
        evaluation_attributes["user_feedback.session_id"] = session_id
        evaluation_attributes["user_feedback.qa_id"] = qa_id
        evaluation_attributes["user_feedback.evaluation_count"] = len([k for k in evaluation_attributes.keys() if k.startswith("evals.") and k.endswith(".score")])
        
        # Try to add attributes to the current span if it's still active
        current_span = trace.get_current_span()
        if current_span and hasattr(current_span, 'get_span_context'):
            current_span_id = str(current_span.get_span_context().span_id)
            if current_span_id == str(primary_span_id):
                # We're in the context of the target span, add attributes directly
                for key, value in evaluation_attributes.items():
                    current_span.set_attribute(key, value)
                logger.info(f"Added {len(evaluation_attributes)} evaluation attributes to active span {primary_span_id}")
                return True
        
        # If we can't add to the active span, create a linked evaluation span
        # This will appear as an annotation in Phoenix
        from .core import create_span
        from .constants import SpanNames, OpenInferenceSpanKind, SpanAttributes
        
        # Create a linked evaluation span that references the original span
        with create_span(
            name=f"{SpanNames.USER_FEEDBACK}.{qa_id}",
            attributes={
                SpanAttributes.SESSION_ID: session_id,
                SpanAttributes.QA_ID: qa_id,
                "span_id": str(primary_span_id),  # Reference to the evaluated span
                "evaluation_type": "user_feedback",
                "openinference.span.kind": OpenInferenceSpanKind.EVALUATOR,
                **evaluation_attributes  # Add all evaluation attributes
            },
            session_id=session_id,
            kind=OpenInferenceSpanKind.EVALUATOR
        ) as eval_span:
            # Add span link to connect this evaluation to the original span
            # This creates a proper parent-child or reference relationship
            eval_span.set_attribute("links.target_span_id", str(primary_span_id))
            eval_span.set_attribute("links.relationship", "evaluates")
            
            logger.info(f"Created linked evaluation span with {len(evaluation_attributes)} feedback attributes")
            logger.info(f"Linked to span: {primary_span_id}")
            
            return True
        
    except Exception as e:
        logger.error(f"Error in feedback association: {e}", exc_info=True)
        return False