"""
Phoenix Native Telemetry System for ATLAS

This module provides comprehensive observability with Phoenix OpenInference compliance,
proper span hierarchy, session management, and advanced feedback tracking.

Features:
- Phoenix native tracing with span-level feedback
- OpenTelemetry fallback compatibility
- Structured evaluation metrics
- Proper span hierarchy for RAG pipelines
"""

# Core telemetry functionality
from .core import (
    initialize_telemetry,
    telemetry_initialized,
    is_telemetry_enabled,
    set_user_telemetry_preference,
    using_session,
    create_span,
    log_user_feedback,
    create_rag_pipeline_span,
    create_retrieval_span,
    create_llm_span as create_llm_span_core,
    create_feedback_span,
    set_span_outputs
)

# Constants and configuration
from .constants import (
    SpanAttributes,
    SpanNames,
    OpenInferenceSpanKind
)

# OpenTelemetry SpanKind for compatibility
from opentelemetry.trace import SpanKind

from .config_attrs import (
    get_test_target_attributes
)

# Phoenix native feedback models
from .feedback import (
    UserFeedback,
    FeedbackResponse,
    associate_feedback_with_spans
)

# API router
from .api import router as telemetry_router

# OpenTelemetry status and utilities
from opentelemetry.trace.status import Status, StatusCode

# Specialized span creation
from .spans import (
    trace_operation,
    create_llm_span,
    create_retriever_span,
    create_human_query_span,
    create_guardrail_span,
    register_span,
    find_qa_span_id,
    find_session_root_span_id,
    find_span_by_trace_id,
    register_session_root_span
)

# Export all public components
__all__ = [
    # Core functionality
    "initialize_telemetry",
    "telemetry_initialized",
    "is_telemetry_enabled",
    "set_user_telemetry_preference",
    "using_session",
    "create_span",
    "log_user_feedback",
    "create_rag_pipeline_span",
    "create_retrieval_span", 
    "create_llm_span",
    "create_feedback_span",
    "set_span_outputs",
    
    # Constants
    "SpanAttributes",
    "SpanNames", 
    "OpenInferenceSpanKind",
    "SpanKind",
    "get_test_target_attributes",
    
    # Feedback models
    "UserFeedback",
    "FeedbackResponse",
    "associate_feedback_with_spans",
    
    # API router
    "telemetry_router",
    
    # Specialized span operations
    "trace_operation",
    "create_llm_span",
    "create_retriever_span",
    "create_human_query_span",
    "create_guardrail_span",
    
    # Span registry functions
    "register_span",
    "find_qa_span_id",
    "find_session_root_span_id", 
    "find_span_by_trace_id",
    "register_session_root_span",
    
    # Status types
    "Status",
    "StatusCode",
    
    # Trace functions from module
    "trace_document_retrieval",
    "trace_llm_generation",
    "trace_document_filtering",
    "trace_citation_formatting",
]

# Initialize telemetry system gracefully
try:
    initialize_telemetry()
except Exception as e:
    import logging
    logger = logging.getLogger(__name__)
    logger.warning(f"Telemetry initialization failed, running in disabled mode: {e}")
    # Continue with telemetry disabled - functions will return no-ops

# Create trace wrapper functions for backward compatibility
from contextlib import contextmanager
from typing import Dict, Any, Optional

@contextmanager
def trace_document_retrieval(session_id: str = None, qa_id: str = None, **kwargs):
    """Create a document retrieval span with proper span kind"""
    attributes = {
        SpanAttributes.SESSION_ID: session_id,
        SpanAttributes.QA_ID: qa_id,
        "span.kind": "RETRIEVER",  # Explicit span kind for Phoenix
        "openinference.span.kind": OpenInferenceSpanKind.RETRIEVER,
        **kwargs
    }
    with create_span(
        SpanNames.CONTEXT_RETRIEVAL,
        attributes=attributes,
        session_id=session_id,
        kind=OpenInferenceSpanKind.RETRIEVER,
        otel_kind=SpanKind.INTERNAL
    ) as span:
        yield span

@contextmanager
def trace_llm_generation(query: str, model_name: str, session_id: str = None, qa_id: str = None, **kwargs):
    """Create an LLM generation span with proper span kind"""
    attributes = {
        SpanAttributes.SESSION_ID: session_id,
        SpanAttributes.QA_ID: qa_id,
        SpanAttributes.INPUT_VALUE: query,
        SpanAttributes.LLM_MODEL: model_name,
        "span.kind": "LLM",  # Explicit span kind for Phoenix
        "openinference.span.kind": OpenInferenceSpanKind.LLM,
        **kwargs
    }
    with create_span(
        SpanNames.LLM_GENERATION,
        attributes=attributes,
        session_id=session_id,
        kind=OpenInferenceSpanKind.LLM,
        otel_kind=SpanKind.INTERNAL
    ) as span:
        yield span

@contextmanager
def trace_document_filtering(session_id: str = None, qa_id: str = None, **kwargs):
    """Create a document filtering span with proper span kind"""
    attributes = {
        SpanAttributes.SESSION_ID: session_id,
        SpanAttributes.QA_ID: qa_id,
        "span.kind": "PROCESSOR",  # Explicit span kind for Phoenix
        "openinference.span.kind": OpenInferenceSpanKind.PROCESSOR,
        **kwargs
    }
    with create_span(
        SpanNames.DOCUMENT_FILTERING,
        attributes=attributes,
        session_id=session_id,
        kind=OpenInferenceSpanKind.PROCESSOR,
        otel_kind=SpanKind.INTERNAL
    ) as span:
        yield span

@contextmanager
def trace_citation_formatting(session_id: str = None, qa_id: str = None, **kwargs):
    """Create a citation formatting span with proper span kind"""
    attributes = {
        SpanAttributes.SESSION_ID: session_id,
        SpanAttributes.QA_ID: qa_id,
        "span.kind": "REFERENCES",  # Explicit span kind for Phoenix
        "openinference.span.kind": OpenInferenceSpanKind.REFERENCES,
        **kwargs
    }
    with create_span(
        SpanNames.DOCUMENT_REFERENCES,
        attributes=attributes,
        session_id=session_id,
        kind=OpenInferenceSpanKind.REFERENCES,
        otel_kind=SpanKind.INTERNAL
    ) as span:
        yield span

# Alias for backward compatibility
OpenInferenceOpenInferenceSpanKind = OpenInferenceSpanKind
