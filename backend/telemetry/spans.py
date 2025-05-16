"""
Specialized span creation for different parts of the ATLAS application.

This module provides context managers and functions for creating spans
for specific operations like LLM calls, retrieval, etc.
"""

import logging
from datetime import datetime
from typing import Dict, Any, Optional, ContextManager
from contextlib import contextmanager

from opentelemetry.trace import SpanKind
from opentelemetry.trace import format_span_id as otel_format_span_id
from openinference.instrumentation.langchain import get_current_span

from .core import create_span, tracer
from .constants import SpanAttributes, OpenInferenceSpanKind, SpanNames

logger = logging.getLogger(__name__)


@contextmanager
def trace_operation(
    operation_name: str,
    attributes: Dict[str, Any] = None,
    session_id: str = None,
    qa_id: str = None,
    kind: SpanKind = SpanKind.CLIENT,
    openinference_kind: str = OpenInferenceSpanKind.CHAIN,
    input_data: Any = None,
    parent_context = None
) -> ContextManager:
    """
    Create a span for a synchronous operation with consistent naming.
    
    Args:
        operation_name: Name of the operation (use SpanNames constants)
        attributes: Dictionary of attributes to add to the span
        session_id: Session ID for association with larger trace
        qa_id: Question/answer ID for this interaction
        kind: Kind of span (default: CLIENT)
        openinference_kind: OpenInference span kind for Phoenix
        input_data: Optional input data to record
        parent_context: Optional parent context to use
        
    Yields:
        The created span
    """
    if attributes is None:
        attributes = {}


    # Add session and QA IDs if provided
    if session_id:
        attributes[SpanAttributes.SESSION_ID] = session_id
    if qa_id:
        attributes[SpanAttributes.QA_ID] = qa_id
    
    # Add OpenInference attributes for Phoenix
    attributes["openinference.span.kind"] = openinference_kind
    
    # Add timestamp
    attributes["timestamp"] = datetime.now().isoformat()
    
    # Add input data if provided
    if input_data is not None:
        if isinstance(input_data, str):
            attributes["input"] = input_data
        elif isinstance(input_data, dict):
            attributes["input"] = str(input_data)
    
    # Create and yield the span
    with create_span(
        operation_name=operation_name,
        attributes=attributes,
        context=parent_context,
        kind=kind,
        session_id=session_id
    ) as span:
        yield span

def add_test_target_attributes(span, include_all=True):
    """
    Add test target configuration attributes to a span.
    
    Args:
        span: The span to add attributes to
        include_all: Whether to include all test target configuration
    """
    # Get current test target from environment
    import os
    test_target = os.getenv('TEST_TARGET', 'unknown')
    
    # Add test target to span
    span.set_attribute(SpanAttributes.TEST_TARGET, test_target)
    
    # Try to import the test target module
    try:
        import importlib
        target_module = importlib.import_module(f"backend.targets.{test_target}")
        
        # Add basic attributes
        if hasattr(target_module, 'TARGET_ID'):
            span.set_attribute(f"{SpanAttributes.TEST_TARGET_PREFIX}id", target_module.TARGET_ID)
        
        if hasattr(target_module, 'MODEL'):
            span.set_attribute(SpanAttributes.LLM_MODEL, target_module.MODEL)
        
        # Add detailed configuration if requested
        if include_all:
            if hasattr(target_module, 'EMBEDDING_MODEL'):
                span.set_attribute(SpanAttributes.EMBEDDING_MODEL, target_module.EMBEDDING_MODEL)
            
            if hasattr(target_module, 'SEARCH_TYPE'):
                span.set_attribute(SpanAttributes.RETRIEVAL_SEARCH_TYPE, target_module.SEARCH_TYPE)
            
            if hasattr(target_module, 'SEARCH_K'):
                span.set_attribute(SpanAttributes.RETRIEVAL_K, target_module.SEARCH_K)
            
            if hasattr(target_module, 'FETCH_K'):
                span.set_attribute(SpanAttributes.RETRIEVAL_FETCH_K, target_module.FETCH_K)
            
            if hasattr(target_module, 'CITATION_LIMIT'):
                span.set_attribute(SpanAttributes.CITATION_LIMIT, target_module.CITATION_LIMIT)
            
            if hasattr(target_module, 'SYSTEM_PROMPT'):
                span.set_attribute(SpanAttributes.SYSTEM_PROMPT, target_module.SYSTEM_PROMPT)
    except Exception as e:
        logger.warning(f"Failed to add test target attributes: {e}")

def record_model_attributes(span, model_name, latency_ms=None, prompt=None, temperature=None):
    """
    Record common LLM attributes to a span following Phoenix conventions.
    
    Args:
        span: The span to add attributes to
        model_name: Name of the language model
        latency_ms: Latency in milliseconds (if known)
        prompt: Prompt used (if available)
        temperature: Temperature setting (if known)
    """
    # Set required OpenInference attributes
    span.set_attribute("openinference.span.kind", OpenInferenceSpanKind.LLM)
    span.set_attribute("openinference.llm.model_name", model_name)
    
    # Set optional attributes if provided
    if latency_ms is not None:
        span.set_attribute("openinference.llm.latency_ms", latency_ms)
    
    if prompt is not None:
        span.set_attribute("openinference.llm.prompt_template", prompt)
    
    if temperature is not None:
        span.set_attribute("openinference.llm.temperature", temperature)
    
    # Add standard ATLAS attributes
    span.set_attribute(SpanAttributes.LLM_MODEL, model_name)

@contextmanager
def create_llm_span(
    query: str,
    model_name: str,
    session_id: str,
    qa_id: str,
    prompt: str = None,
    temperature: float = None,
    attributes: Dict[str, Any] = None
):
    """
    Create a dedicated LLM span following Phoenix best practices.
    
    Args:
        query: User query/question
        model_name: Name of the language model 
        session_id: Session identifier
        qa_id: Question-answer identifier
        prompt: Prompt template (if available)
        temperature: Temperature setting (if known)
        attributes: Additional attributes (optional)
        
    Returns:
        Context manager for the LLM span
    """
    if attributes is None:
        attributes = {}
    
    # Add required OpenInference attributes
    span_attributes = {
        **attributes,
        SpanAttributes.SESSION_ID: session_id,
        SpanAttributes.QA_ID: qa_id,
        "openinference.llm.model_name": model_name,
        "openinference.llm.input": query
    }
    
    # Add optional attributes if provided
    if prompt is not None:
        span_attributes["openinference.llm.prompt_template"] = prompt
    
    if temperature is not None:
        span_attributes["openinference.llm.temperature"] = temperature
    
    # Create span with proper kind
    with trace_operation(
        SpanNames.LLM_GENERATION,
        attributes=span_attributes,
        session_id=session_id,
        qa_id=qa_id,
        openinference_kind=OpenInferenceSpanKind.LLM,
        input_data=query
    ) as span:
        # Add test target attributes
        add_test_target_attributes(span)
        yield span

@contextmanager
def create_retriever_span(
    query: str,
    session_id: str,
    qa_id: str,
    retriever_type: str,
    top_k: int = None,
    attributes: Dict[str, Any] = None
):
    """
    Create a dedicated retriever span following Phoenix best practices.
    
    Args:
        query: Search query
        session_id: Session identifier
        qa_id: Question-answer identifier
        retriever_type: Type of retriever (e.g., "vector", "hybrid")
        top_k: Number of documents to retrieve
        attributes: Additional attributes (optional)
        
    Returns:
        Context manager for the retriever span
    """
    if attributes is None:
        attributes = {}
    
    # Add required OpenInference attributes
    span_attributes = {
        **attributes,
        SpanAttributes.SESSION_ID: session_id,
        SpanAttributes.QA_ID: qa_id,
        "openinference.retriever.type": retriever_type,
        "openinference.retriever.query": query
    }
    
    # Add optional attributes if provided
    if top_k is not None:
        span_attributes["openinference.retriever.top_k"] = top_k
    
    # Create span with proper kind
    with trace_operation(
        SpanNames.CONTEXT_RETRIEVAL,
        attributes=span_attributes,
        session_id=session_id,
        qa_id=qa_id,
        openinference_kind=OpenInferenceSpanKind.RETRIEVER,
        input_data=query
    ) as span:
        # Add test target attributes
        add_test_target_attributes(span)
        yield span

@contextmanager
def create_human_query_span(
    query: str,
    session_id: str,
    qa_id: str,
    attributes: Dict[str, Any] = None
):
    """
    Create a span for a human query/input.
    
    Args:
        query: User query/question
        session_id: Session identifier
        qa_id: Question-answer identifier
        attributes: Additional attributes (optional)
        
    Returns:
        Context manager for the human query span
    """
    if attributes is None:
        attributes = {}
    
    # Add required OpenInference attributes for human interactions
    span_attributes = {
        **attributes,
        SpanAttributes.SESSION_ID: session_id,
        "session.id": session_id,
        SpanAttributes.QA_ID: qa_id,
        "input": query,
        "openinference.agent.input": query,
        "role": "human",  # Add explicit role
        "timestamp": datetime.now().isoformat()
    }
    
    # Create span with proper kind
    with trace_operation(
        "com.atlas.human.query",
        attributes=span_attributes,
        session_id=session_id,
        qa_id=qa_id,
        openinference_kind=OpenInferenceSpanKind.HUMAN,
        input_data=query,
        kind=SpanKind.CONSUMER  # CONSUMER kind for incoming requests
    ) as span:
        yield span

# Track spans for deduplication
_current_spans = {}

# Registry to store span IDs by session and QA ID
_span_registry = {}

def get_current_span_id():
    """Get the current span ID as a hex string."""
    current_span = get_current_span()
    if current_span:
        return otel_format_span_id(current_span.get_span_context().span_id)
    return None

def register_span(session_id, qa_id, span_id):
    """
    Register a span ID for a specific session and QA ID.
    This allows feedback to be linked to the original span later.
    
    Args:
        session_id: Session ID
        qa_id: Question/answer ID
        span_id: Span ID as a hex string
    """
    global _span_registry
    
    if not session_id or not qa_id or not span_id:
        return
    
    # Create session entry if it doesn't exist
    if session_id not in _span_registry:
        _span_registry[session_id] = {}
    
    # Store span ID for this QA ID
    _span_registry[session_id][qa_id] = span_id
    logger.debug(f"Registered span ID {span_id} for session {session_id}, qa_id {qa_id}")

def find_qa_span_id(session_id, qa_id):
    """
    Find the span ID for a specific QA interaction.
    This is used to link feedback to the original QA span.
    
    Args:
        session_id: Session ID
        qa_id: Question/answer ID
        
    Returns:
        str: Span ID as a hex string, or None if not found
    """
    global _span_registry
    
    # Check if we have a registered span ID for this session and QA ID
    if session_id in _span_registry and qa_id in _span_registry[session_id]:
        span_id = _span_registry[session_id][qa_id]
        logger.debug(f"Found registered span ID {span_id} for session {session_id}, qa_id {qa_id}")
        return span_id
    
    # Log detailed information about the missing span
    if session_id in _span_registry:
        available_qa_ids = list(_span_registry[session_id].keys())
        logger.warning(f"No span found for qa_id={qa_id} in session {session_id}. Available qa_ids: {available_qa_ids}")
    else:
        logger.warning(f"Session {session_id} not found in span registry. Registry keys: {list(_span_registry.keys())}")
    
    # Return None instead of falling back to the current span
    # This ensures feedback is only associated with the correct span
    return None
