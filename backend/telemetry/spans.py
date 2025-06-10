"""
Specialized span creation for different parts of the ATLAS application.

This module provides context managers and functions for creating spans
for specific operations like LLM calls, retrieval, etc.
"""

import logging
from datetime import datetime
from typing import Dict, Any, Optional, ContextManager
from contextlib import contextmanager
import time

from opentelemetry import trace
from opentelemetry.trace import SpanKind
from opentelemetry.trace import format_span_id as otel_format_span_id
from opentelemetry.context import get_current

from .core import create_span, tracer
from .constants import SpanAttributes, OpenInferenceSpanKind, SpanNames

logger = logging.getLogger(__name__)

# Try to import get_current_span - fallback if not available
try:
    from openinference.instrumentation.langchain import get_current_span
except ImportError:
    # Fallback to OpenTelemetry's get_current_span with proper context handling
    def get_current_span():
        # Get current context first
        current_context = get_current()
        
        # Try to get span from current context
        current_span = trace.get_current_span(current_context)
        
        # If no span in current context, try the global tracer
        if not current_span or not current_span.is_recording():
            current_span = trace.get_current_span()
            
        return current_span if current_span and current_span.is_recording() else None


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
    
    # Add OpenInference attributes for Phoenix - use official standard only
    attributes["openinference.span.kind"] = openinference_kind
    
    # Add timestamp - using high precision for proper ordering
    attributes["timestamp"] = datetime.now().isoformat()
    attributes["start_time"] = time.time()  # High precision start time for ordering
    
    # Add explicit sequence number for reliable ordering within each query
    if session_id and qa_id:
        # QA-specific sequence counter for this specific query
        counter_key = f"_sequence_counter_{session_id}_{qa_id}"
        if not hasattr(trace_operation, counter_key):
            setattr(trace_operation, counter_key, 0)
        current_count = getattr(trace_operation, counter_key) + 1
        setattr(trace_operation, counter_key, current_count)
        attributes["span.sequence"] = current_count
        attributes["span.order"] = current_count  # Alternative name for Phoenix
        
        # Clean up old counters to prevent memory leaks (keep only recent ones)
        if current_count == 1:  # First span in this QA, cleanup old ones
            attrs_to_remove = [attr for attr in dir(trace_operation) 
                             if attr.startswith("_sequence_counter_") and attr != counter_key]
            # Remove oldest counters, keep only most recent 50
            if len(attrs_to_remove) > 50:
                for attr in attrs_to_remove[:-50]:  # Remove all but last 50
                    try:
                        delattr(trace_operation, attr)
                    except AttributeError:
                        pass
    
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
                # Use the current context more robustly
                parent_context = trace.set_span_in_context(current_span, get_current())
    
    # Create and yield the span
    with create_span(
        name=operation_name,
        attributes=attributes,
        session_id=session_id,
        kind=openinference_kind,
        otel_kind=kind,
        parent_context=parent_context
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
        
        # Add basic attributes with consolidated naming (remove duplication)
        if hasattr(target_module, 'TARGET_ID'):
            span.set_attribute("test_target.id", target_module.TARGET_ID)
        
        if hasattr(target_module, 'MODEL'):
            span.set_attribute(SpanAttributes.LLM_MODEL, target_module.MODEL)
            span.set_attribute("test_target.model", target_module.MODEL)
        
        # Add detailed configuration if requested
        if include_all:
            if hasattr(target_module, 'EMBEDDING_MODEL'):
                span.set_attribute("test_target.embedding_model", target_module.EMBEDDING_MODEL)
            
            if hasattr(target_module, 'SEARCH_TYPE'):
                span.set_attribute("test_target.search_type", target_module.SEARCH_TYPE)
            
            if hasattr(target_module, 'SEARCH_K'):
                span.set_attribute("test_target.search_k", target_module.SEARCH_K)
            
            if hasattr(target_module, 'FETCH_K'):
                span.set_attribute("test_target.fetch_k", target_module.FETCH_K)
            
            if hasattr(target_module, 'CITATION_LIMIT'):
                span.set_attribute("test_target.citation_limit", target_module.CITATION_LIMIT)
            
            if hasattr(target_module, 'SYSTEM_PROMPT'):
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

@contextmanager
def create_guardrail_span(
    guardrail_type: str,
    input_text: str,
    session_id: str,
    qa_id: str,
    enabled: bool = True,
    attributes: Dict[str, Any] = None,
    parent_context = None
):
    """
    Create a span for a guardrail check.
    
    This span represents a guardrail/safety check in the RAG pipeline.
    
    Args:
        guardrail_type: Type of guardrail (e.g., "sensitivity", "toxicity", "pii")
        input_text: Text being checked
        session_id: Session identifier
        qa_id: Question-answer identifier
        enabled: Whether the guardrail is actively enforcing (vs just monitoring)
        attributes: Additional attributes (optional)
        parent_context: Optional parent context for explicit hierarchy
        
    Returns:
        Context manager for the guardrail span
    """
    if attributes is None:
        attributes = {}
    
    # Add required OpenInference attributes for guardrails
    span_attributes = {
        **attributes,
        # Session identifiers
        SpanAttributes.SESSION_ID: session_id,
        SpanAttributes.QA_ID: qa_id,
        
        # Input text
        SpanAttributes.INPUT_VALUE: input_text,
        "query_length": len(input_text),
        
        # Guardrail metadata
        "guardrail.type": guardrail_type,
        "guardrail.enabled": enabled,
        
        # Span classification
        "openinference.span.kind": OpenInferenceSpanKind.GUARDRAIL,
        
        # Timestamp
        "timestamp": datetime.now().isoformat()
    }
    
    # Create span with proper kind and explicit parent context if provided
    with trace_operation(
        f"com.atlas.guardrails.{guardrail_type}",
        attributes=span_attributes,
        session_id=session_id,
        qa_id=qa_id,
        openinference_kind=OpenInferenceSpanKind.GUARDRAIL,
        input_data=input_text,
        kind=SpanKind.INTERNAL,
        parent_context=parent_context,  # Use explicit parent context
        link_to_current=False if parent_context else True  # Only link to current if no explicit parent
    ) as span:
        yield span

# Import the span registry
from .registry import span_registry

# Legacy support - redirect to registry for backward compatibility
_span_registry = {}

# Flag to indicate we're using the new registry system
_using_registry = True

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

def register_span(session_id, qa_id, span_id, trace_id=None):
    """
    Register a span ID for a specific session and QA pair.
    This allows finding spans later for feedback association.
    
    Args:
        session_id: Session identifier
        qa_id: Question-answer identifier
        span_id: Span identifier
        trace_id: Optional trace identifier for Phoenix correlation
    """
    # Use the registry for registration
    span_registry.register_span(session_id, qa_id, str(span_id), trace_id)
    
    # For backward compatibility, also update in-memory registry
    if not _using_registry:
        global _span_registry
        
        if not session_id:
            logger.warning("Cannot register span without session_id")
            return
            
        # Initialize session entry if needed
        if session_id not in _span_registry:
            _span_registry[session_id] = {}
        
        # Store the span ID as string
        if qa_id is not None:
            span_id_str = str(span_id)
            _span_registry[session_id][qa_id] = span_id_str

def find_qa_span_id(session_id, qa_id):
    """
    Find a span ID for a specific session and QA pair.
    """
    # Use registry to find span
    return span_registry.find_span(session_id, qa_id)

def find_session_root_span_id(session_id: str) -> Optional[str]:
    """
    Find the root span ID for a session.
    
    Args:
        session_id: Session ID
        
    Returns:
        Root span ID if found, None otherwise
    """
    # Use registry to find root span
    return span_registry.find_root_span(session_id)


def register_session_root_span(session_id: str, span_id: str, trace_id: Optional[str] = None):
    """
    Register a root span for a session.
    
    Args:
        session_id: Session identifier
        span_id: Span identifier
        trace_id: Optional trace identifier for Phoenix correlation
    """
    span_registry.register_root_span(session_id, str(span_id), trace_id)


def find_span_by_trace_id(trace_id: str) -> Optional[str]:
    """
    Find a span by its trace ID.
    
    Args:
        trace_id: Trace identifier for Phoenix correlation
        
    Returns:
        Span ID if found, None otherwise
    """
    return span_registry.find_span_by_trace(trace_id)


def update_span_attributes(span_id: str, attributes: Dict[str, Any]) -> bool:
    """
    Update a span with the given attributes directly, without creating a separate span.
    This function is specifically designed for attaching feedback to existing spans.
    
    Args:
        span_id: The ID of the span to update
        attributes: Dictionary of attributes to add to the span
        
    Returns:
        True if the span was successfully updated, False otherwise
    """
    if not span_id:
        logger.warning("Cannot update span attributes: no span_id provided")
        return False
        
    try:
        # Attempt 1: Try using Phoenix API if available
        try:
            import phoenix
            if hasattr(phoenix, 'update_span'):
                # Direct Phoenix API call if available
                success = phoenix.update_span(span_id, attributes)
                if success:
                    logger.info(f"Updated span {span_id} using Phoenix API")
                    return True
        except ImportError:
            pass
            
        # Attempt 2: Try OpenTelemetry's get_tracer().get_span method if available
        try:
            from opentelemetry import trace
            tracer = trace.get_tracer(__name__)
            if hasattr(tracer, 'get_span'):
                span = tracer.get_span(span_id)
                if span:
                    for key, value in attributes.items():
                        span.set_attribute(key, value)
                    logger.info(f"Updated span {span_id} using OpenTelemetry API")
                    return True
        except (ImportError, AttributeError):
            pass
            
        # Attempt 3: Create a feedback.annotator span that manually sets these attributes
        # on its parent span with explicit links
        from .core import create_span
        from .constants import SpanNames, OpenInferenceSpanKind
        
        with create_span(
            name=f"{SpanNames.FEEDBACK_ANNOTATOR}",
            attributes={
                "feedback.target_span_id": span_id,
                "feedback.annotator": "true",
                "feedback.is_annotation": "true",
                "openinference.span.kind": OpenInferenceSpanKind.ANNOTATOR
            }
        ) as annotator_span:
            # Add special attributes that Phoenix might recognize
            annotator_span.set_attribute("links.target_span_id", span_id)
            annotator_span.set_attribute("links.relationship", "annotates")
            annotator_span.set_attribute("target.span_id", span_id)
            
            # Add all the feedback attributes
            for key, value in attributes.items():
                annotator_span.set_attribute(f"target.{key}", value)
                
            logger.info(f"Created annotator span for {span_id}")
            return True
            
    except Exception as e:
        logger.error(f"Failed to update span {span_id}: {e}", exc_info=True)
        return False
