"""
This module provides functions for detecting sensitive contexts in user queries.
Currently a placeholder for future implementation of guardrails for culturally 
or ethically sensitive topics.
"""

import logging
import time
from typing import List, Tuple, Optional

from backend.telemetry.spans import create_guardrail_span

# Define context types for hierarchical classification
SENSITIVITY_TYPES = {
    'cultural': ['indigenous_au', 'indigenous_nz'],
    'ethical': ['medical', 'legal'],
    # More categories can be added as needed
}

# Keep geographic contexts for backward compatibility
# These will eventually be replaced by user-controlled corpus selection
GEOGRAPHIC_CONTEXTS = {
    'geographic': ['au', 'nz', 'uk'],
}

def detect_sensitive_contexts(query: str, session_id: Optional[str] = None, qa_id: Optional[str] = None, parent_span=None) -> list:
    """
    Detect sensitive contexts in a query with confidence scoring.
    Currently returns an empty list as sensitivity detection is disabled.
    
    Reserved for future implementation of guardrails for sensitive topics.
    
    Args:
        query: The user query string
        session_id: Optional session ID for telemetry
        qa_id: Optional QA ID for telemetry
        parent_span: Optional parent span for explicit hierarchy
        
    Returns:
        Empty list (for now) - will later return [(context_code, confidence_score)]
    """
    # Create a guardrail span to track sensitivity detection
    # Use explicit parent context if provided
    parent_context = None
    if parent_span:
        from opentelemetry import trace
        from opentelemetry.context import get_current
        parent_context = trace.set_span_in_context(parent_span, get_current())
    
    with create_guardrail_span(
        guardrail_type="sensitivity",
        input_text=query,
        session_id=session_id,
        qa_id=qa_id,
        enabled=False,  # Currently disabled
        parent_context=parent_context
    ) as span:
        start_time = time.time()
        
        # Log the call for debugging purposes
        logging.debug(f"Sensitive context detection called for query: {query}")
        
        # Future implementation will go here
        # For now, returning an empty list
        sensitive_contexts = []
        
        # Calculate processing time
        processing_time = time.time() - start_time
        
        # Set span attributes for the results
        span.set_attribute("guardrail.triggered", len(sensitive_contexts) > 0)
        span.set_attribute("guardrail.result", "pass" if len(sensitive_contexts) == 0 else "fail")
        span.set_attribute("detected_sensitivities", sensitive_contexts)
        span.set_attribute("sensitivity_count", len(sensitive_contexts))
        span.set_attribute("processing_time_ms", processing_time * 1000)
        
        # Add summary
        if sensitive_contexts:
            summary = f"Detected {len(sensitive_contexts)} sensitive contexts"
            span.set_attribute("summary", summary)
            span.set_attribute("output", summary)
        else:
            summary = "No sensitive contexts detected"
            span.set_attribute("summary", summary)
            span.set_attribute("output", summary)
        
        return sensitive_contexts

def get_primary_sensitivity(sensitive_contexts):
    """
    Get the highest confidence sensitivity from the detected contexts.
    
    Args:
        sensitive_contexts: List of (context_code, confidence) tuples
        
    Returns:
        The context code with highest confidence, or None if no contexts detected
    """
    if not sensitive_contexts:
        return None
        
    return sensitive_contexts[0][0]

# For backward compatibility with old code
detect_context_conditions = detect_sensitive_contexts
get_primary_context = get_primary_sensitivity 