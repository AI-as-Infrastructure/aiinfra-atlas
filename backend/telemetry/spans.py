"""
Specialized span creation for different parts of the ATLAS application.

This module provides context managers and functions for creating spans
for specific operations like LLM calls, retrieval, etc.
"""

import logging
from datetime import datetime
from typing import Dict, Any, Optional, ContextManager
from contextlib import contextmanager

from opentelemetry import trace
from opentelemetry.trace import SpanKind
from opentelemetry.trace import format_span_id as otel_format_span_id

from .core import create_span, tracer
from .constants import SpanAttributes, OpenInferenceSpanKind, SpanNames

logger = logging.getLogger(__name__)

# Try to import get_current_span - fallback if not available
try:
    from openinference.instrumentation.langchain import get_current_span
except ImportError:
    # Fallback to OpenTelemetry's get_current_span
    def get_current_span():
        return trace.get_current_span()


@contextmanager
def trace_operation(
    operation_name: str,
    attributes: Dict[str, Any] = None,
    session_id: str = None,
    qa_id: str = None,
    kind: SpanKind = SpanKind.CLIENT,
    openinference_kind: str = OpenInferenceSpanKind.CHAIN,
    input_data: Any = None,
    parent_context = None,
    link_to_current: bool = False
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
        link_to_current: Whether to link to the current span as parent
        
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
    
    # Add OpenInference attributes for Phoenix - ensure the structure matches Phoenix format
    attributes["openinference.span.kind"] = openinference_kind
    
    # Add timestamp
    attributes["timestamp"] = datetime.now().isoformat()
    
    # Add input data if provided
    if input_data is not None:
        if isinstance(input_data, str):
            attributes["input.value"] = input_data
        elif isinstance(input_data, dict):
            for key, value in input_data.items():
                if isinstance(value, (str, int, float, bool)):
                    attributes[f"input.{key}"] = value
    
    # If link_to_current is True and no specific parent_context is provided, 
    # try to get the current span as parent
    if link_to_current and parent_context is None:
        current_span = get_current_span()
        if current_span and hasattr(current_span, 'get_span_context'):
            current_context = current_span.get_span_context()
            if hasattr(current_context, 'is_valid') and current_context.is_valid:
                parent_context = trace.set_span_in_context(current_span)
    
    # Create and yield the span
    with create_span(
        name=operation_name,
        attributes=attributes,
        session_id=session_id,
        kind=openinference_kind
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
        
        # Add basic attributes with flattened structure
        if hasattr(target_module, 'TARGET_ID'):
            span.set_attribute(f"{SpanAttributes.TEST_TARGET_PREFIX}id", target_module.TARGET_ID)
            span.set_attribute("test_target.id", target_module.TARGET_ID)
        
        if hasattr(target_module, 'MODEL'):
            span.set_attribute(SpanAttributes.LLM_MODEL, target_module.MODEL)
            span.set_attribute("test_target.model", target_module.MODEL)
        
        # Add detailed configuration if requested
        if include_all:
            if hasattr(target_module, 'EMBEDDING_MODEL'):
                span.set_attribute(SpanAttributes.EMBEDDING_MODEL, target_module.EMBEDDING_MODEL)
                span.set_attribute("test_target.embedding_model", target_module.EMBEDDING_MODEL)
            
            if hasattr(target_module, 'SEARCH_TYPE'):
                span.set_attribute(SpanAttributes.RETRIEVAL_SEARCH_TYPE, target_module.SEARCH_TYPE)
                span.set_attribute("test_target.search_type", target_module.SEARCH_TYPE)
            
            if hasattr(target_module, 'SEARCH_K'):
                span.set_attribute(SpanAttributes.RETRIEVAL_K, target_module.SEARCH_K)
                span.set_attribute("test_target.search_k", target_module.SEARCH_K)
            
            if hasattr(target_module, 'FETCH_K'):
                span.set_attribute(SpanAttributes.RETRIEVAL_FETCH_K, target_module.FETCH_K)
                span.set_attribute("test_target.fetch_k", target_module.FETCH_K)
            
            if hasattr(target_module, 'CITATION_LIMIT'):
                span.set_attribute(SpanAttributes.CITATION_LIMIT, target_module.CITATION_LIMIT)
                span.set_attribute("test_target.citation_limit", target_module.CITATION_LIMIT)
            
            if hasattr(target_module, 'SYSTEM_PROMPT'):
                span.set_attribute(SpanAttributes.SYSTEM_PROMPT, target_module.SYSTEM_PROMPT)
                span.set_attribute("test_target.system_prompt", target_module.SYSTEM_PROMPT)
            
            # Add any other target attributes that might be useful
            for attr_name in dir(target_module):
                if attr_name.isupper() and not attr_name.startswith('__') and attr_name not in [
                    'TARGET_ID', 'MODEL', 'EMBEDDING_MODEL', 'SEARCH_TYPE', 
                    'SEARCH_K', 'FETCH_K', 'CITATION_LIMIT', 'SYSTEM_PROMPT'
                ]:
                    try:
                        value = getattr(target_module, attr_name)
                        if isinstance(value, (str, int, float, bool)):
                            span.set_attribute(f"test_target.{attr_name.lower()}", value)
                    except Exception as e:
                        logger.debug(f"Could not add test target attribute {attr_name}: {e}")
        
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
    # Set required OpenInference attributes using the proper nested structure
    span.set_attribute("openinference", {
        "span": {
            "kind": OpenInferenceSpanKind.LLM
        },
        "llm": {
            "model_name": model_name
        }
    })
    
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
    
    This span represents the user's question that initiates the RAG process.
    It's designed to appear as a child span of the RAG pipeline.
    
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
        # Session identifiers
        SpanAttributes.SESSION_ID: session_id,
        "session.id": session_id,
        SpanAttributes.QA_ID: qa_id,
        
        # User input
        "input.value": query,
        
        # Span classification
        "openinference.span.kind": OpenInferenceSpanKind.HUMAN,
        "openinference.human.input": query,
        "role": "human",
        "human.role": "user",
        "human.description": "User query that initiates the RAG process",
        
        # Timestamp
        "timestamp": datetime.now().isoformat()
    }
    
    # Create span with proper kind and ensure it's linked to current context (parent)
    with trace_operation(
        SpanNames.HUMAN_QUERY,
        attributes=span_attributes,
        session_id=session_id,
        qa_id=qa_id,
        openinference_kind=OpenInferenceSpanKind.HUMAN,
        input_data=query,
        kind=SpanKind.CONSUMER,  # CONSUMER kind for incoming requests
        link_to_current=True  # Explicitly link to current context (parent)
    ) as span:
        # Register this span for the qa_id
        current_span_id = otel_format_span_id(span.get_span_context().span_id)
        register_span(session_id, qa_id, current_span_id)
        
        yield span

# Global span registry for tracking spans across sessions
_span_registry = {}

def get_current_span_id():
    """Get the current span ID as a hex string."""
    try:
        # Try Phoenix native first
        import phoenix as px
        current_span = px.trace.get_current_span()
        if current_span:
            return str(current_span.span_id)
    except ImportError:
        pass
    
    # Fallback to OpenTelemetry
    current_span = get_current_span()
    if current_span:
        return otel_format_span_id(current_span.get_span_context().span_id)
    return None

def register_span(session_id, qa_id, span_id):
    """
    Register a span ID for a specific session and QA pair.
    This allows finding spans later for feedback association.
    Works with both Phoenix native and OpenTelemetry spans.
    
    Args:
        session_id: Session ID
        qa_id: Question/answer ID, or special key
        span_id: Span ID (Phoenix span object or OpenTelemetry span ID)
    """
    global _span_registry
    
    if not session_id:
        logger.warning("Cannot register span without session_id")
        return
        
    # Initialize session entry if needed
    if session_id not in _span_registry:
        _span_registry[session_id] = {}
    
    # Store the span ID or span object
    if qa_id is not None:  # Allow None or empty string as qa_id values
        _span_registry[session_id][qa_id] = span_id
        
        # Special logging for response spans to aid debugging
        if qa_id and isinstance(qa_id, str) and qa_id.endswith("_response"):
            logger.info(f"Registered response span for session={session_id}, qa_id={qa_id}, span_id={span_id}")
        else:
            logger.debug(f"Registered span for session={session_id}, qa_id={qa_id}, span_id={span_id}")

def find_qa_span_id(session_id, qa_id):
    """
    Find a span ID for a specific session and QA pair.
    Returns Phoenix span object if available, otherwise OpenTelemetry span ID.
    
    Args:
        session_id: Session ID
        qa_id: Question/answer ID
        
    Returns:
        Span ID/object if found, None otherwise
    """
    global _span_registry
    
    if not session_id or qa_id is None:
        return None
        
    # Check if session exists in registry
    if session_id not in _span_registry:
        logger.warning(f"Session {session_id} not found in registry")
        return None
    
    # Check if qa_id exists in session
    if qa_id not in _span_registry[session_id]:
        # Special handling for response span keys
        if isinstance(qa_id, str) and qa_id.endswith("_response"):
            # Log the miss but don't show it as a warning
            logger.info(f"Response span for qa_id={qa_id} not found in session={session_id}")
        else:
            logger.info(f"QA ID {qa_id} not found in session {session_id}")
            
        # Log available keys for debugging
        available_keys = list(_span_registry[session_id].keys())
        if available_keys:
            logger.info(f"Available qa_ids for session {session_id}: {available_keys}")
        return None
    
    # Return the span ID/object
    span_id = _span_registry[session_id][qa_id]
    
    # Special logging for response spans
    if isinstance(qa_id, str) and qa_id.endswith("_response"):
        logger.info(f"Found response span for qa_id={qa_id} in session={session_id}: span_id={span_id}")
    else:
        logger.debug(f"Found span for qa_id={qa_id} in session={session_id}: span_id={span_id}")
        
    return span_id

def find_session_root_span_id(session_id: str) -> Optional[int]:
    """
    Find the root span ID for a session.
    
    Args:
        session_id: Session ID
        
    Returns:
        Root span ID if found, None otherwise
    """
    global _span_registry
    
    try:
        # First check the registry for the root span (qa_id=None)
        if session_id in _span_registry:
            # Check for the root span (qa_id=None)
            if None in _span_registry[session_id]:
                return _span_registry[session_id][None]
            
            # If no root span is explicitly registered, use the first span ID
            if _span_registry[session_id]:
                # Get the first qa_id (any will do for linking)
                first_qa_id = next(iter(_span_registry[session_id]))
                return _span_registry[session_id][first_qa_id]
                
        return None
    except Exception as e:
        logger.error(f"Error finding session root span: {e}", exc_info=True)
        return None
