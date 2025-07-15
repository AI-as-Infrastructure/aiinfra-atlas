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
from contextvars import ContextVar

# Context variable to track user telemetry preference for the current request
_user_telemetry_enabled: ContextVar[bool] = ContextVar('user_telemetry_enabled', default=True)

# Phoenix native imports for proper span management
try:
    import phoenix as px
    from phoenix.trace import using_project
    PHOENIX_AVAILABLE = True
except ImportError as e:
    # Don't raise error immediately - check if telemetry is disabled first
    PHOENIX_AVAILABLE = False
    px = None
    using_project = None
    _phoenix_import_error = e

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

@contextmanager  
def no_op_span():
    """Return a no-op context manager when telemetry is disabled"""
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
    
    # Check if Phoenix is available when telemetry is enabled
    if not PHOENIX_AVAILABLE:
        global _phoenix_import_error
        logger.error(f"❌ CRITICAL: Phoenix telemetry is enabled but Phoenix package is not available: {_phoenix_import_error}")
        raise ImportError(f"Phoenix telemetry is required but not available: {_phoenix_import_error}")
    
    # Get Phoenix configuration from environment
    phoenix_endpoint = os.getenv("PHOENIX_COLLECTOR_ENDPOINT")
    _project_name = os.getenv("PHOENIX_PROJECT_NAME", "atlas-telemetry")
    
    # For Phoenix Arize Cloud, use PHOENIX_CLIENT_HEADERS
    phoenix_client_headers = os.getenv("PHOENIX_CLIENT_HEADERS")

    # ---- Sanitize and ensure correct header format ----
    if phoenix_client_headers:
        # Remove any surrounding quotes/newlines and whitespace
        phoenix_client_headers = phoenix_client_headers.strip().strip('"').strip("'").strip()

        # Check if it's JSON format first
        try:
            import json
            hdr_dict = json.loads(phoenix_client_headers)
            if isinstance(hdr_dict, dict):
                # Ensure the project_name field is present
                hdr_dict["project_name"] = _project_name  # Always override with env value
                phoenix_client_headers = ",".join(f"{k}={v}" for k, v in hdr_dict.items())
        except json.JSONDecodeError:
            # Header is already in comma-separated form; ensure project_name is present and correct
            headers_dict = {}
            for pair in phoenix_client_headers.split(","):
                if "=" in pair:
                    k, v = pair.split("=", 1)
                    headers_dict[k.strip()] = v.strip()
            
            # Always set project_name from environment variable
            headers_dict["project_name"] = _project_name
            phoenix_client_headers = ",".join(f"{k}={v}" for k, v in headers_dict.items())
    # ---------------------------------------------------
    
    if not phoenix_endpoint:
        logger.warning("PHOENIX_COLLECTOR_ENDPOINT not configured - telemetry will be disabled")
        _telemetry_initialized = True  # Mark as initialized but disabled
        return False
    
    if not phoenix_client_headers:
        logger.warning("PHOENIX_CLIENT_HEADERS not configured - telemetry will be disabled")
        _telemetry_initialized = True  # Mark as initialized but disabled
        return False

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

        # Add standard batch processor for spans
        # Using very short delay (100ms) for proper chronological span ordering
        span_processor = BatchSpanProcessor(
            otlp_exporter,
            schedule_delay_millis=100,    # Export every 100ms for proper ordering
            max_export_batch_size=50,     # Smaller batches for faster export
            export_timeout_millis=2000    # 2 second timeout
        )
        tracer_provider.add_span_processor(span_processor)


        # Set as global tracer provider
        otel_trace.set_tracer_provider(tracer_provider)

        # Get tracer instance
        _tracer = tracer_provider.get_tracer("atlas.telemetry")
        _phoenix_session = True

        logger.info(f"Phoenix Arize online tracing initialized for project: {_project_name}")
        _telemetry_initialized = True
        return True
    except Exception as e:
        logger.error(f" Failed to initialize Phoenix telemetry: {e}")
        logger.warning("Phoenix telemetry initialization failed - telemetry will be disabled")
        _telemetry_initialized = True  # Mark as initialized but disabled
        return False

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
        # If Phoenix isn't available, yield a no-op span
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
        return
    with using_project(_project_name):
        yield session_id

def is_telemetry_enabled(request=None) -> bool:
    """
    Check if telemetry is enabled based on environment variable and user preference.
    
    Checks both:
    1. TELEMETRY_ENABLED environment variable (system-wide control)
    2. User preference via context variable or request headers (user control)
    
    If system telemetry is disabled, returns False regardless of user preference.
    If system telemetry is enabled, respects user preference (no headers = privacy enabled).
    
    Args:
        request: Optional FastAPI/Flask request object to check for telemetry headers
        
    Returns:
        bool: True if telemetry should be enabled, False otherwise
        
    Examples:
        export TELEMETRY_ENABLED=false  # Disables telemetry system-wide
        export TELEMETRY_ENABLED=true   # Enables telemetry, respects user preference
    """
    # First check system-wide telemetry setting
    value = os.getenv("TELEMETRY_ENABLED", "true").strip()
    if not value:  # Handle empty string case
        system_enabled = True
    else:
        system_enabled = value.lower() in ("true", "1", "yes", "on")
    
    # If system telemetry is disabled, respect that
    if not system_enabled:
        return False
    
    # Check user preference via context variable (set by middleware) or request headers
    try:
        user_enabled = _user_telemetry_enabled.get()
        if not user_enabled:
            return False
    except LookupError:
        # Context variable not set, check request headers if available
        if request:
            trace_id = getattr(request, 'headers', {}).get("X-Trace-Id")
            if not trace_id:
                return False
    
    return True

def set_user_telemetry_preference(request) -> bool:
    """
    Set user telemetry preference based on request headers.
    
    Args:
        request: FastAPI request object
        
    Returns:
        bool: True if user has enabled telemetry, False if privacy is enabled
    """
    # Check if user has sent telemetry headers (privacy off) or not (privacy on)
    trace_id = getattr(request, 'headers', {}).get("X-Trace-Id")
    user_enabled = bool(trace_id)
    
    # Set in context variable for this request
    _user_telemetry_enabled.set(user_enabled)
    
    return user_enabled

from opentelemetry.trace import SpanKind

@contextmanager
def create_span(name: str, attributes: Dict[str, Any] = None, 
               session_id: str = None, kind: Any = None, otel_kind: Any = None,
               parent_context = None) -> ContextManager:
    """
    Create a telemetry span using Phoenix native tracing for proper feedback support
    
    Args:
        name: Span operation name
        attributes: Span attributes
        session_id: Session identifier
        kind: OpenInference span kind string (for Phoenix logical kind)
        otel_kind: OpenTelemetry protocol span kind (e.g., SpanKind.INTERNAL, SpanKind.SERVER, etc.)
        parent_context: Optional parent context for explicit span hierarchy
    """
    # Check if telemetry is enabled
    if not is_telemetry_enabled():
        # Yield a no-op span when telemetry is disabled
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
        return
    
    # Prepare attributes
    span_attributes = attributes or {}
    
    # Add session ID if provided
    if session_id:
        span_attributes[SpanAttributes.SESSION_ID] = session_id
    
    # Add OpenInference span kind - only if not already provided
    if kind:
        # Only set if not already provided in attributes to avoid overwriting trace_operation settings
        if SpanAttributes.OPENINFERENCE_SPAN_KIND not in span_attributes:
            span_attributes[SpanAttributes.OPENINFERENCE_SPAN_KIND] = kind
        if "openinference.span.kind" not in span_attributes:
            span_attributes["openinference.span.kind"] = kind  # Use OpenInference standard only
    
    # Check if Phoenix is available and initialized
    if not PHOENIX_AVAILABLE or not _phoenix_session or not _tracer:
        # If Phoenix isn't available or disabled, yield a no-op span
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
        return
    
    # Use OpenTelemetry with Phoenix OTLP exporter inside Phoenix project context
    tracer = get_tracer()
    # Set OpenTelemetry protocol span kind if provided, else default to INTERNAL
    protocol_kind = otel_kind if otel_kind is not None else SpanKind.INTERNAL
    
    # Always create spans within the Phoenix project context
    with using_project(_project_name):
        # Use parent_context if provided for proper span hierarchy
        if parent_context:
            with tracer.start_as_current_span(name, context=parent_context, attributes=span_attributes, kind=protocol_kind) as span:
                yield span
        else:
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
            "openinference.span.kind": OpenInferenceSpanKind.CHAIN,  # OpenInference standard only
            **kwargs
        },
        session_id=session_id,
        kind=OpenInferenceSpanKind.CHAIN
    )
    
    # Register the span for feedback association
    def _register_span_on_enter(span):
        # Check if telemetry is disabled first
        if not is_telemetry_enabled():
            return span
            
        from .spans import register_span, register_session_root_span
        from opentelemetry.trace import format_span_id as otel_format_span_id
        if not PHOENIX_AVAILABLE or not _phoenix_session:
            # When telemetry is enabled but Phoenix is not available, this is an error
            # When telemetry is disabled, we already returned above
            raise RuntimeError("Phoenix telemetry is not available for span registration.")
        
        # Get the span ID as hex string
        span_id = otel_format_span_id(span.get_span_context().span_id)
        
        # Register as the main pipeline span
        register_span(session_id, qa_id, span_id)
        
        # Register as the session root ONLY if one hasn't been registered yet (to avoid multiple roots per session)
        try:
            from backend.telemetry.spans import find_session_root_span_id
            current_root = find_session_root_span_id(session_id)
            if not current_root:
                register_session_root_span(session_id, span_id)
        except Exception:
            # If any lookup fails, fallback to registering (previous behaviour)
            register_session_root_span(session_id, span_id)
        
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
        # Check if telemetry is disabled first
        if not is_telemetry_enabled():
            return span
            
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
        # Check if telemetry is disabled first
        if not is_telemetry_enabled():
            return span
            
        from .spans import register_span
        from opentelemetry.trace import format_span_id as otel_format_span_id
        if not PHOENIX_AVAILABLE or not _phoenix_session:
            raise RuntimeError("Phoenix telemetry is not available for span registration.")
        
        # Get the span ID as hex string
        span_id = otel_format_span_id(span.get_span_context().span_id)
        
        # Register as the main response span for feedback
        # Note: We only register with the response key to avoid duplicate registrations
        register_span(session_id, f"{qa_id}_response", span_id)
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

async def log_user_feedback(session_id: str, qa_id: str, feedback_data: Dict[str, Any]) -> bool:
    """Log user feedback by associating it with the appropriate span."""
    logger.info(f"CORE: log_user_feedback called with session_id={session_id}, qa_id={qa_id}")
    logger.info(f"CORE: feedback_data keys: {list(feedback_data.keys())}")
    logger.info(f"CORE: sentiment in feedback_data: {'sentiment' in feedback_data}")
    logger.info(f"CORE: sentiment value: {feedback_data.get('sentiment')}")
    
    if not is_telemetry_enabled():
        logger.info("Telemetry disabled - skipping feedback logging")
        return True  # Return True to indicate "success" even when disabled
    
    from .feedback import associate_feedback_with_spans
    return await associate_feedback_with_spans(session_id, qa_id, feedback_data)

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
            return
        
        # For Phoenix spans, check if span context is valid
        if hasattr(span, 'get_span_context'):
            context = span.get_span_context()
            if hasattr(context, 'is_valid') and not context.is_valid():
                return
    except Exception:
        pass
    try:
        # Use Phoenix-standard output attributes only
        if summary:
            span.set_attribute("summary", summary)
        if details:
            span.set_attribute("details", details)
        if output:
            span.set_attribute("output", output)  # Primary Phoenix output field
        if error:
            span.set_attribute("error", True)
            span.set_attribute("error.message", str(error))
            span.set_attribute("error.type", error.__class__.__name__)
            span.record_exception(error)
    except Exception as e:
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