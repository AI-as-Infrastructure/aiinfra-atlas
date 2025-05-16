"""
RAG-specific telemetry for the ATLAS application.

This module provides specialized telemetry functions for the RAG pipeline,
including document retrieval, context processing, and LLM generation.
"""

import logging
from typing import Dict, Any, List, Optional
from contextlib import contextmanager
from datetime import datetime

from .core import create_span
from .spans import trace_operation, add_test_target_attributes
from .constants import SpanAttributes, OpenInferenceSpanKind, SpanNames

logger = logging.getLogger(__name__)

@contextmanager
def trace_document_retrieval(session_id: str, qa_id: str):
    """Create a span for document retrieval operations."""
    with create_span(
        SpanNames.CONTEXT_RETRIEVAL,
        attributes={
            SpanAttributes.SESSION_ID: session_id,
            SpanAttributes.QA_ID: qa_id,
            "openinference.span.kind": OpenInferenceSpanKind.RETRIEVER
        },
        session_id=session_id
    ) as span:
        yield span

@contextmanager
def trace_document_filtering(session_id: str, qa_id: str):
    """Create a span for document filtering and ranking operations."""
    with create_span(
        SpanNames.DOCUMENT_RANKING,
        attributes={
            SpanAttributes.SESSION_ID: session_id,
            SpanAttributes.QA_ID: qa_id,
            "openinference.span.kind": OpenInferenceSpanKind.RERANKER
        },
        session_id=session_id
    ) as span:
        yield span

@contextmanager
def trace_citation_formatting(session_id: str, qa_id: str):
    """Create a span for citation formatting operations."""
    with create_span(
        SpanNames.CITATION_FORMATTING,
        attributes={
            SpanAttributes.SESSION_ID: session_id,
            SpanAttributes.QA_ID: qa_id,
            "openinference.span.kind": OpenInferenceSpanKind.CHAIN
        },
        session_id=session_id
    ) as span:
        yield span

from contextlib import contextmanager

@contextmanager
def trace_llm_generation(
    query: str,
    model_name: str,
    session_id: str,
    qa_id: str,
    prompt: str,
    context_document_count: int,
    output: str = None
):
    """
    Create a span for LLM generation operations.
    Optionally set the LLM output as an attribute after response generation.
    """
    with create_span(
        SpanNames.LLM_GENERATION,
        attributes={
            SpanAttributes.SESSION_ID: session_id,
            SpanAttributes.QA_ID: qa_id,
            SpanAttributes.INPUT_VALUE: query,
            "openinference.llm.model_name": model_name,
            "openinference.llm.prompt": prompt,
            "openinference.span.kind": OpenInferenceSpanKind.LLM,
            "context_document_count": context_document_count
        },
        session_id=session_id
    ) as span:
        try:
            yield span
        finally:
            # If output is provided, set it as an attribute on the span
            if output is not None:
                # Set Phoenix/OpenInference output field for UI
                if hasattr(span, "set_output"):
                    span.set_output(output)
                span.set_attribute("output.value", output)
                # Retain legacy attributes for compatibility
                span.set_attribute("openinference.llm.output", output)
                span.set_attribute("openinference.agent.output", output)
                span.set_attribute("role", "assistant")


def log_session_config(session_id: str, config_data: Dict[str, Any] = None):
    """
    Log the current configuration to Phoenix for experimental tracking.
    Only the most important fields are flattened for easy querying.
    The full config is included as a single nested object for completeness.
    """
    if not session_id:
        logger.warning("Cannot log session config without session_id")
        return False

    try:
        from backend.telemetry.config_attrs import get_test_target_attributes
        from backend.telemetry.spans import register_span
        test_target_attrs = get_test_target_attributes()

        # Merge config_data (if present) with test_target_attrs, config_data takes precedence
        merged_config = dict(test_target_attrs)
        if config_data:
            merged_config.update(config_data)

        # Select key fields to flatten for Phoenix queries
        important_keys = [
            "target_id", "llm_model", "embedding_model", "search_type", "search_k",
            "citation_limit", "algorithm", "chunk_size", "chunk_overlap",
            "index_name", "llm_provider", "composite_target", "ATLAS_VERSION"
        ]
        attributes = {
            SpanAttributes.SESSION_ID: session_id,
            "timestamp": datetime.now().isoformat(),
        }
        for key in important_keys:
            if key in merged_config:
                attributes[key] = merged_config[key]

        # Add the full config as a single nested object for completeness
        attributes["test_target_config"] = merged_config

        # Create the configuration span with all attributes
        with create_span(
            SpanNames.SESSION_CONFIGURATION,
            attributes=attributes,
            session_id=session_id
        ) as span:
            # Register this span as the root for the session (qa_id=None)
            register_span(session_id, qa_id=None, span_id=span.get_span_context().span_id)
            logger.info(f"Logged configuration for session {session_id} with {len(attributes)} attributes (root span, cleaned)")
            return True
    except Exception as e:
        logger.error(f"Failed to log session configuration: {e}", exc_info=True)
        return False
