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
    using_session,
    create_span,
    log_user_feedback,
    create_rag_pipeline_span,
    create_retrieval_span,
    create_llm_span,
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

# Export all public components
__all__ = [
    # Core functionality
    "initialize_telemetry",
    "telemetry_initialized",
    "is_telemetry_enabled",
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
    
    # OpenTelemetry utilities
    "Status",
    "StatusCode"
]

# Initialize telemetry system
initialize_telemetry()
