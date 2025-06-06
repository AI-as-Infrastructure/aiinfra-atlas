"""
Enhanced Telemetry Core for ATLAS Application

This module provides the core telemetry functionality with Phoenix native tracing
for proper span-level feedback association as recommended by Phoenix Arize.
"""

import os
import uuid
import logging
from contextlib import contextmanager
from typing import Dict, Any, Optional, ContextManager

# Phoenix native imports for proper span management
try:
    import phoenix as px
    from phoenix.trace import using_project
    PHOENIX_AVAILABLE = True
except ImportError as e:
    raise ImportError("Phoenix telemetry is required but the 'phoenix' package is not installed.") from e

from .constants import SpanAttributes, SpanNames, OpenInferenceSpanKind
from opentelemetry.trace import SpanKind

# Configure logging
logger = logging.getLogger(__name__)

# Global telemetry state
_telemetry_initialized = False
_phoenix_session = None
_tracer = None
_project_name = None
_telemetry_enabled = True  # Track if telemetry is actually enabled

def initialize_telemetry() -> bool:
    """
    Initialize the Phoenix native telemetry system for proper feedback association
    Raises an error if Phoenix is not available or not configured correctly.
    Returns:
        bool: True if initialization successful, False otherwise
    """
    global _telemetry_initialized, _phoenix_session, _tracer, _project_name
    
    if _telemetry_initialized:
        logger.info("Telemetry already initialized")
        return True
    
    # Check if telemetry is enabled via environment variable
    telemetry_enabled = is_telemetry_enabled()
    
    if not telemetry_enabled:
        logger.info("🚫 Telemetry disabled via TELEMETRY_ENABLED environment variable")
        _telemetry_initialized = True  # Mark as initialized but disabled
        return False
    
    # Get Phoenix configuration from environment
    phoenix_endpoint = os.getenv("PHOENIX_COLLECTOR_ENDPOINT")
    _project_name = os.getenv("PHOENIX_PROJECT_NAME", "atlas-telemetry")
    
    # For Phoenix Arize Cloud, use PHOENIX_CLIENT_HEADERS
    phoenix_client_headers = os.getenv("PHOENIX_CLIENT_HEADERS")
    
    if not phoenix_endpoint:
        raise RuntimeError("PHOENIX_COLLECTOR_ENDPOINT environment variable is required for Phoenix telemetry.")
    
    if not phoenix_client_headers:
        raise RuntimeError("PHOENIX_CLIENT_HEADERS environment variable is required for Phoenix Arize Cloud.")

    try:
        # Set OTEL environment variables for Phoenix Arize Cloud
        # According to Phoenix docs, use OTEL_EXPORTER_OTLP_HEADERS with api_key (underscore)
        os.environ["OTEL_EXPORTER_OTLP_TRACES_ENDPOINT"] = f"{phoenix_endpoint}/v1/traces"
        os.environ["OTEL_EXPORTER_OTLP_HEADERS"] = phoenix_client_headers
        os.environ["OTEL_EXPORTER_OTLP_PROTOCOL"] = "http/protobuf"
        # Append or update project.name in OTEL_RESOURCE_ATTRIBUTES without overwriting other attributes
        existing_attrs = os.environ.get("OTEL_RESOURCE_ATTRIBUTES", "")
        attrs = {}
        if existing_attrs:
            for pair in existing_attrs.split(","):
                if pair.strip():
                    k, _, v = pair.partition("=")
                    attrs[k.strip()] = v.strip()
        attrs["project.name"] = _project_name
        os.environ["OTEL_RESOURCE_ATTRIBUTES"] = ",".join(f"{k}={v}" for k, v in attrs.items())
        logger.info(f"OTEL_RESOURCE_ATTRIBUTES set to: {os.environ['OTEL_RESOURCE_ATTRIBUTES']}")

        logger.info(f"Setting OTEL_EXPORTER_OTLP_HEADERS for Phoenix Arize Cloud authentication")

        # Use standard OpenTelemetry setup
        from opentelemetry import trace as otel_trace
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
        from opentelemetry.sdk.resources import Resource

        # Create resource with service information
        resource = Resource.create({
            "service.name": "atlas",
            "service.version": "1.0.0",
            "project.name": _project_name,
        })

        # Create tracer provider
        tracer_provider = TracerProvider(resource=resource)

        # Create OTLP exporter - it will use the environment variables we set
        otlp_exporter = OTLPSpanExporter()

        # Add debug wrapper to verify spans are being exported
        original_export = otlp_exporter.export
        def debug_export(spans):
            span_ids = [str(span.context.span_id) for span in spans]
            logger.info(f"Exporting {len(spans)} spans to Phoenix: {span_ids[:5]}{'...' if len(span_ids) > 5 else ''}")
            try:
                result = original_export(spans)
                logger.info(f"Export result: {result}")
                return result
            except Exception as e:
                logger.error(f"Error exporting spans: {e}")
                raise
        otlp_exporter.export = debug_export

        # Add standard batch processor for spans
        # Using default settings (5-second delay) for more responsive feedback
        span_processor = BatchSpanProcessor(
            otlp_exporter,
            # Use default delay (5 seconds) for more responsive span export
            # max_export_batch_size=512 (using default)
        )
        tracer_provider.add_span_processor(span_processor)

        logger.info(" Configured BatchSpanProcessor with 5-second delay for feedback association")

        # Set as global tracer provider
        otel_trace.set_tracer_provider(tracer_provider)

        # Get tracer instance
        _tracer = tracer_provider.get_tracer("atlas.telemetry")
        _phoenix_session = True

        logger.info(f" Phoenix Arize online tracing initialized")
        logger.info(f" Project: {_project_name}")
        logger.info(f" Endpoint: {phoenix_endpoint}")
        _telemetry_initialized = True
        return True
    except Exception as e:
        logger.error(f" Failed to initialize Phoenix telemetry: {e}")
        import traceback
        traceback.print_exc()
        raise RuntimeError(f"Failed to initialize Phoenix telemetry: {e}")

def get_tracer():
    """Get the tracer instance (Phoenix only, fails if not initialized)"""
    if not _telemetry_initialized:
        raise RuntimeError("Telemetry not initialized. Call initialize_telemetry() first.")
    if not _tracer:
        raise RuntimeError("Phoenix tracer is not initialized.")
    return _tracer

@contextmanager
def using_session(session_id: str = None, metadata: Dict[str, Any] = None):
    """
    Context manager for session-scoped operations using Phoenix native session management
    Raises if Phoenix is not available.
    """
    if not session_id:
        session_id = str(uuid.uuid4())
    if not PHOENIX_AVAILABLE or not _phoenix_session:
        raise RuntimeError("Phoenix telemetry session is not available. Ensure Phoenix is configured and initialized.")
    with using_project(_project_name):
        yield session_id

def is_telemetry_enabled() -> bool:
    """
    Check if telemetry is enabled via environment variable.
    
    The TELEMETRY_ENABLED environment variable controls whether telemetry
    is active. When disabled, all telemetry operations become no-ops.
    
    Accepted values for enabling telemetry:
    - "true", "1", "yes", "on" (case-insensitive)
    - Empty string or unset (defaults to enabled)
    
    Accepted values for disabling telemetry:
    - "false", "0", "no", "off" (case-insensitive)
    - Any other value
    
    Returns:
        bool: True if telemetry should be enabled, False otherwise
        
    Examples:
        export TELEMETRY_ENABLED=false  # Disables telemetry
        export TELEMETRY_ENABLED=true   # Enables telemetry
        unset TELEMETRY_ENABLED         # Defaults to enabled
    """
    value = os.getenv("TELEMETRY_ENABLED", "true").strip()
    if not value:  # Handle empty string case
        return True
    return value.lower() in ("true", "1", "yes", "on")

from opentelemetry.trace import SpanKind

@contextmanager
def create_span(name: str, attributes: Dict[str, Any] = None, 
               session_id: str = None, kind: Any = None, otel_kind: Any = None) -> ContextManager:
    """
    Create a telemetry span using Phoenix native tracing for proper feedback support
    
    Args:
        name: Span operation name
        attributes: Span attributes
        session_id: Session identifier
        kind: OpenInference span kind string (for Phoenix logical kind)
        otel_kind: OpenTelemetry protocol span kind (e.g., SpanKind.INTERNAL, SpanKind.SERVER, etc.)
    """
    # Check if telemetry is enabled
    if not is_telemetry_enabled():
        # Return a no-op context manager when telemetry is disabled
        @contextmanager
        def no_op_span():
            class NoOpSpan:
                def set_attribute(self, key, value):
                    pass
                def set_status(self, status):
                    pass
                def record_exception(self, exception):
                    pass
                def get_span_context(self):
                    class NoOpContext:
                        span_id = 0
                        def is_valid(self):
                            return False
                    return NoOpContext()
            yield NoOpSpan()
        return no_op_span()
    
    # Prepare attributes
    span_attributes = attributes or {}
    
    # Add session ID if provided
    if session_id:
        span_attributes[SpanAttributes.SESSION_ID] = session_id
    
    # Add OpenInference span kind
    if kind:
        span_attributes[SpanAttributes.OPENINFERENCE_SPAN_KIND] = kind
    
    if not PHOENIX_AVAILABLE or not _phoenix_session:
        raise RuntimeError("Phoenix telemetry is not available. Ensure Phoenix is configured and initialized.")
    
    # Use OpenTelemetry with Phoenix OTLP exporter
    tracer = get_tracer()
    # Set OpenTelemetry protocol span kind if provided, else default to INTERNAL
    protocol_kind = otel_kind if otel_kind is not None else SpanKind.INTERNAL
    with tracer.start_as_current_span(name, attributes=span_attributes, kind=protocol_kind) as span:
        yield span

def create_rag_pipeline_span(session_id: str, qa_id: str, query: str, **kwargs):
    """Create a RAG pipeline span directly without span factory"""
    span_context = create_span(
        SpanNames.RAG_PIPELINE,
        attributes={
            SpanAttributes.SESSION_ID: session_id,
            SpanAttributes.QA_ID: qa_id,
            SpanAttributes.INPUT_VALUE: query,
            "span.kind": "CHAIN",  # Explicit span kind for Phoenix
            "openinference.span.kind": OpenInferenceSpanKind.CHAIN,  # OpenInference span kind
            **kwargs
        },
        session_id=session_id,
        kind=OpenInferenceSpanKind.CHAIN
    )
    
    # Register the span for feedback association
    def _register_span_on_enter(span):
        from .spans import register_span, register_session_root_span
        from opentelemetry.trace import format_span_id as otel_format_span_id
        if not PHOENIX_AVAILABLE or not _phoenix_session:
            raise RuntimeError("Phoenix telemetry is not available for span registration.")
        
        # Get the span ID as hex string
        span_id = otel_format_span_id(span.get_span_context().span_id)
        
        # Register as the main pipeline span
        register_span(session_id, qa_id, span_id)
        
        # Also register as the root span for the session - this is crucial for feedback association
        register_session_root_span(session_id, span_id)
        
        logger.info(f"Registered RAG pipeline as root span: session={session_id}, qa_id={qa_id}, span_id={span_id}")
        return span
    
    # Wrap the context manager to register the span
    @contextmanager
    def _wrapped_span():
        with span_context as span:
            yield _register_span_on_enter(span)
    
    return _wrapped_span()

def create_retrieval_span(session_id: str, qa_id: str, query: str, **kwargs):
    """Create a document retrieval span directly without span factory"""
    span_context = create_span(
        SpanNames.CONTEXT_RETRIEVAL,
        attributes={
            SpanAttributes.SESSION_ID: session_id,
            SpanAttributes.QA_ID: qa_id,
            SpanAttributes.INPUT_VALUE: query,
            **kwargs
        },
        session_id=session_id,
        kind=OpenInferenceSpanKind.RETRIEVER
    )
    
    # Register the span for feedback association
    def _register_span_on_enter(span):
        from .spans import register_span
        from opentelemetry.trace import format_span_id as otel_format_span_id
        if not PHOENIX_AVAILABLE or not _phoenix_session:
            raise RuntimeError("Phoenix telemetry is not available for span registration.")
        # Register the span ID as hex string for proper feedback association
        span_id = otel_format_span_id(span.get_span_context().span_id)
        register_span(session_id, f"{qa_id}_retrieval", span_id)
        return span
    
    @contextmanager
    def _wrapped_span():
        with span_context as span:
            yield _register_span_on_enter(span)
    
    return _wrapped_span()

def create_llm_span(session_id: str, qa_id: str, model: str, **kwargs):
    """Create an LLM generation span directly without span factory"""
    span_context = create_span(
        SpanNames.LLM_GENERATION,
        attributes={
            SpanAttributes.SESSION_ID: session_id,
            SpanAttributes.QA_ID: qa_id,
            SpanAttributes.LLM_MODEL: model,
            **kwargs
        },
        session_id=session_id,
        kind=OpenInferenceSpanKind.LLM
    )
    
    # Register the span for feedback association - this is the key span for feedback
    def _register_span_on_enter(span):
        from .spans import register_span
        from opentelemetry.trace import format_span_id as otel_format_span_id
        if not PHOENIX_AVAILABLE or not _phoenix_session:
            raise RuntimeError("Phoenix telemetry is not available for span registration.")
        
        # Get the span ID as hex string
        span_id = otel_format_span_id(span.get_span_context().span_id)
        
        # Register as the main response span for feedback
        # Note: We only register with the response key to avoid duplicate registrations
        register_span(session_id, f"{qa_id}_response", span_id)
        logger.info(f"Registered LLM response span: session={session_id}, qa_id={qa_id}, span_id={span_id}")
        return span
    
    @contextmanager
    def _wrapped_span():
        with span_context as span:
            yield _register_span_on_enter(span)
    
    return _wrapped_span()

def create_child_span(parent_span_id: str, name: str, attributes: Dict[str, Any] = None, kind: Any = None):
    """
    Create a span that is explicitly a child of another span using the parent's span_id
    
    Args:
        parent_span_id: The ID of the parent span
        name: Span operation name
        attributes: Span attributes
        kind: OpenInference span kind string
    """
    from .registry import span_registry
    import logging
    
    logger = logging.getLogger(__name__)
    
    # Skip if telemetry is disabled
    if not is_telemetry_enabled():
        return no_op_span()
    
    # Default attributes
    if attributes is None:
        attributes = {}
    
    try:
        # Try to get parent span context from registry
        parent_context = span_registry.get_span_context(parent_span_id)
        
        if not parent_context:
            logger.warning(f"Parent span {parent_span_id} not found in registry. Creating detached span.")
            # Fall back to a regular span if parent not found
            return create_span(name, attributes, kind=kind)
        
        # Set the parent span ID attribute for explicit linking
        attributes["parent_span_id"] = parent_span_id
        
        # Get tracer
        tracer = get_tracer()
        
        # Create a span with link to parent context
        span_context = tracer.start_span(
            name=name,
            context=parent_context,  # This makes it a child of the parent span
            attributes=attributes,
            kind=kind
        )
        
        # Register the new span
        span_id = uuid.uuid4().hex
        span_registry.register_span(span_id, span_context)
        
        # Return the span with its context for use in a with statement
        @contextmanager
        def _span_context():
            try:
                yield span_context
            finally:
                span_context.end()
        
        return _span_context()
    except Exception as e:
        logger.error(f"Error creating child span: {e}")
        return no_op_span()

def create_feedback_span(session_id: str, qa_id: str, feedback_data: Dict[str, Any], **kwargs):
    """Create a feedback span directly without span factory"""
    return create_span(
        SpanNames.USER_FEEDBACK,
        attributes={
            SpanAttributes.SESSION_ID: session_id,
            SpanAttributes.QA_ID: qa_id,
            **feedback_data,
            **kwargs
        },
        session_id=session_id,
        kind=OpenInferenceSpanKind.HUMAN
    )

def log_user_feedback(session_id: str, qa_id: str, feedback_data: Dict[str, Any]) -> bool:
    """Log user feedback by associating it with the appropriate span."""
    if not is_telemetry_enabled():
        logger.info("Telemetry disabled - skipping feedback logging")
        return True  # Return True to indicate "success" even when disabled
    
    from .feedback import associate_feedback_with_spans
    return associate_feedback_with_spans(session_id, qa_id, feedback_data)

def set_span_outputs(span, summary: str = None, details: Dict[str, Any] = None, 
                    output: str = None, error: Exception = None):
    """
    Set standard output attributes on a span for Phoenix UI display.
    
    Args:
        span: The span to update
        summary: Brief summary of the operation
        details: Detailed information as a dictionary
        output: Main output content
        error: Exception if an error occurred
    """
    # Check if span is still active to prevent "setting attribute on ended span" warnings
    try:
        # Try to check if span is ended (this works for OpenTelemetry spans)
        if hasattr(span, 'is_recording') and not span.is_recording():
            logger.debug("Skipping attribute setting on ended span")
            return
        
        # For Phoenix spans, check if span context is valid
        if hasattr(span, 'get_span_context'):
            context = span.get_span_context()
            if hasattr(context, 'is_valid') and not context.is_valid():
                logger.debug("Skipping attribute setting on invalid span context")
                return
    except Exception:
        pass
    try:
        if summary:
            span.set_attribute("summary", summary)
        if details:
            span.set_attribute("details", details)
        if output:
            span.set_attribute("content", output)  # Only use Phoenix-recognized key
        if error:
            span.set_attribute("error", True)
            span.set_attribute("error.message", str(error))
            span.set_attribute("error.type", error.__class__.__name__)
            span.record_exception(error)
    except Exception as e:
        logger.debug(f"Error setting span attributes: {e}")
        pass

def is_telemetry_initialized() -> bool:
    """Check if telemetry has been initialized"""
    return _telemetry_initialized

# Backward compatibility alias
def telemetry_initialized() -> bool:
    """Check if telemetry has been initialized (alias for is_telemetry_initialized)"""
    return is_telemetry_initialized()

# Expose tracer for direct access
tracer = get_tracer 

# Note: Telemetry initialization is now handled by the application startup
# instead of at import time to ensure environment variables are loaded first 