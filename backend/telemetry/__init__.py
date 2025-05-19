"""
ATLAS Telemetry System

A unified telemetry system for the ATLAS application using Phoenix Arize.
This module centralizes all telemetry-related functionality, providing
consistent interfaces for trace context propagation, span creation,
and attribute management.
"""

# Import OpenTelemetry classes directly
from opentelemetry.trace import SpanKind, Status, StatusCode

# Import core functionality
from .core import (
    initialize_telemetry,
    create_span,
    create_trace_span,
    extract_trace_context,
    extract_session_info,
    inject_trace_context,
    validate_config,
    using_session,
    tracer,
    tracer_provider,
    telemetry_initialized
)

# Import constants
from .constants import (
    SpanAttributes,
    SpanNames,
    OpenInferenceSpanKind,
    TEST_TARGET_SCHEMA
)

# Import span creation functions
from .spans import (
    trace_operation,
    add_test_target_attributes,
    record_model_attributes,
    create_llm_span,
    create_retriever_span,
    create_human_query_span,
    get_current_span_id,
    find_qa_span_id,
    register_span
)

# Import RAG-specific functions
from .rag import (
    trace_document_retrieval,
    trace_document_filtering,
    trace_llm_generation,
    trace_citation_formatting,
    log_session_config
)

# Import feedback handling
from .feedback import (
    validate_feedback,
    log_user_feedback,
    associate_feedback_with_spans,
    get_rating_name,
    UserFeedback,
    FeedbackResponse
)

# Import API functions
from .api import (
    router as telemetry_router,
    register_telemetry_api
)

# Import span manager
from .span_manager import BaseSpanManager
from .rag_span_manager import RAGSpanManager

# Add this function
def get_span_manager(name, manager_type=BaseSpanManager):
    """Get a span manager with a properly configured tracer.
    
    Args:
        name: Name for the tracer
        manager_type: Type of span manager to create (default: BaseSpanManager)
        
    Returns:
        An instance of the specified span manager type
    """
    from opentelemetry import trace
    tracer = trace.get_tracer(name)
    return manager_type(tracer)

# Export everything for backward compatibility
__all__ = [
    # OpenTelemetry classes
    'SpanKind',
    'Status',
    'StatusCode',
    
    # Core
    'initialize_telemetry',
    'create_span',
    'create_trace_span',
    'extract_trace_context',
    'extract_session_info',
    'inject_trace_context',
    'validate_config',
    'using_session',
    'tracer',
    'tracer_provider',
    'telemetry_initialized',
    
    # Constants
    'SpanAttributes',
    'SpanNames',
    'OpenInferenceSpanKind',
    'TEST_TARGET_SCHEMA',
    
    # Spans
    'trace_operation',
    'add_test_target_attributes',
    'record_model_attributes',
    'create_llm_span',
    'create_retriever_span',
    'create_human_query_span',
    'get_current_span_id',
    'find_qa_span_id',
    'register_span',
    
    # RAG
    'trace_document_retrieval',
    'trace_document_filtering',
    'trace_llm_generation',
    'trace_citation_formatting',
    'log_session_config',
    
    # Feedback
    'validate_feedback',
    'log_user_feedback',
    'associate_feedback_with_spans',
    'get_rating_name',
    'UserFeedback',
    'FeedbackResponse',
    
    # API
    'telemetry_router',
    'register_telemetry_api',
    
    # Span Manager
    'BaseSpanManager',
    'RAGSpanManager',
    'get_span_manager',
]
