"""
Core telemetry functionality for Phoenix Arize integration.

This module provides the foundation for telemetry in the ATLAS application,
handling initialization, trace context management, and basic span creation.
"""

import os
import logging
import json
from typing import Dict, Any, Optional, List, Tuple, Union
from contextlib import contextmanager

# OpenTelemetry imports
from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode, SpanKind, Span
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator
from phoenix.otel import register
from opentelemetry.propagate import extract, inject
from opentelemetry.context import Context, get_current

# Try to import OpenInference for session management
try:
    from openinference.instrumentation import using_session as openinference_using_session
    HAS_OPENINFERENCE = True
except ImportError:
    HAS_OPENINFERENCE = False
    logger = logging.getLogger(__name__)
    logger.error("OpenInference not available. Session tracking will use fallback method.")

# Import constants
from .constants import SpanAttributes

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global tracer provider and tracer
tracer_provider = None
tracer = None

# Track spans for deduplication
_current_spans = {}

def initialize_telemetry(service_name: str = None) -> bool:
    """
    Initialize the telemetry system with Phoenix Arize.
    
    Args:
        service_name: Optional service name for the tracer
        
    Returns:
        bool: True if initialization was successful, False otherwise
    """
    global tracer_provider, tracer
    
    # If already initialized, return
    if tracer is not None:
        return True
    
    # Get configuration from environment variables
    phoenix_project_name = os.getenv('PHOENIX_PROJECT_NAME', 'ATLAS')
    
    # Ensure the collector endpoint has the /v1/traces path
    phoenix_collector_endpoint = os.getenv('PHOENIX_COLLECTOR_ENDPOINT', 'https://app.phoenix.arize.com')
    if not phoenix_collector_endpoint.endswith('/v1/traces'):
        phoenix_collector_endpoint = f"{phoenix_collector_endpoint}/v1/traces"
    
    # Use OTEL protocol from environment
    otel_protocol = os.getenv('OTEL_EXPORTER_OTLP_PROTOCOL')
    if not otel_protocol:
        logger.warning("OTEL_EXPORTER_OTLP_PROTOCOL not set in environment")
    
    try:
        # Get API key from headers (preferred method for hosted Phoenix)
        client_api_key = None
        if os.getenv('PHOENIX_CLIENT_HEADERS', ''):
            headers_str = os.getenv('PHOENIX_CLIENT_HEADERS', '')
            if 'api_key=' in headers_str:
                client_api_key = headers_str.split('api_key=')[1].split(',')[0].strip()
                logger.info("Using API key from PHOENIX_CLIENT_HEADERS")
        
        # Fallback to PHOENIX_API_KEY for backward compatibility
        if not client_api_key:
            client_api_key = os.getenv('PHOENIX_API_KEY', '')
            if client_api_key:
                logger.warning("Using deprecated PHOENIX_API_KEY. Consider switching to PHOENIX_CLIENT_HEADERS.")
        
        # Check if we have a valid API key
        if not client_api_key:
            logger.error("No Phoenix API key found in environment variables")
            return False
            
        logger.info(f"Initializing Phoenix connection for project: {phoenix_project_name}")
        
        # Register the tracer provider with Phoenix
        headers = {"api_key": client_api_key}
        
        tracer_provider = register(
            project_name=phoenix_project_name,
            endpoint=phoenix_collector_endpoint,
            headers=headers,
        )
        
        # Get a tracer from the provider
        tracer = trace.get_tracer(service_name or __name__)
        
        logger.info(f"Phoenix tracing initialized for project: {phoenix_project_name}")
        return True
    except Exception as e:
        logger.error(f"Failed to initialize Phoenix tracing: {e}", exc_info=True)
        tracer = None
        return False

@contextmanager
def using_session(session_id: str):
    """
    Context manager to set the session ID for all spans created within the context.
    This ensures proper session tracking in Phoenix Arize.
    
    Args:
        session_id: The session ID to associate with spans
        
    Yields:
        None
    """
    if not session_id:
        # If no session ID is provided, just yield without setting anything
        yield
        return
    
    if HAS_OPENINFERENCE:
        # Use OpenInference's built-in session context manager if available
        with openinference_using_session(session_id):
            yield
    else:
        # Fallback implementation - we'll rely on our create_span function
        # which already adds session_id to all spans
        yield

def extract_trace_context(carrier: Any) -> Optional[Context]:
    """
    Extract trace context from a carrier object (request, dict, etc.)
    
    Args:
        carrier: Object containing trace context (request, dict, etc.)
        
    Returns:
        Optional[Context]: Extracted trace context or None if not found
    """
    if carrier is None:
        return None
    
    try:
        # Handle different carrier types
        if hasattr(carrier, 'headers'):
            # Request object with headers
            context = extract(TraceContextTextMapPropagator(), carrier.headers)
            return context
        elif isinstance(carrier, dict):
            # Dictionary carrier
            if 'traceparent' in carrier or 'traceId' in carrier:
                context = extract(TraceContextTextMapPropagator(), carrier)
                return context
        
        # Try to access as a generic object
        if hasattr(carrier, 'traceparent') or hasattr(carrier, 'traceId'):
            # Convert object attributes to dict
            headers_dict = {}
            for attr in ['traceparent', 'tracestate', 'traceId', 'spanId']:
                if hasattr(carrier, attr):
                    headers_dict[attr] = getattr(carrier, attr)
            
            if headers_dict:
                context = extract(TraceContextTextMapPropagator(), headers_dict)
                return context
    except Exception as e:
        logger.warning(f"Failed to extract trace context: {e}")
    
    return None

def extract_session_info(carrier: Any) -> Tuple[str, Optional[str]]:
    """
    Extract session ID and QA ID from a carrier object.
    
    Args:
        carrier: Object containing session information
        
    Returns:
        Tuple[str, Optional[str]]: Session ID and QA ID (or None if not found)
    """
    session_id = None
    qa_id = None
    
    try:
        # Handle different carrier types
        if hasattr(carrier, 'headers'):
            # Request object with headers
            session_id = carrier.headers.get('X-Session-ID')
            qa_id = carrier.headers.get('X-QA-ID')
        elif isinstance(carrier, dict):
            # Dictionary carrier
            session_id = carrier.get('session_id') or carrier.get('X-Session-ID')
            qa_id = carrier.get('qa_id') or carrier.get('X-QA-ID')
        
        # Try to access as a generic object
        if not session_id and hasattr(carrier, 'session_id'):
            session_id = getattr(carrier, 'session_id')
        
        if not qa_id and hasattr(carrier, 'qa_id'):
            qa_id = getattr(carrier, 'qa_id')
    except Exception as e:
        logger.warning(f"Failed to extract session info: {e}")
    
    return session_id, qa_id

def inject_trace_context() -> Dict[str, str]:
    """
    Inject the current trace context into a carrier dictionary.
    
    Returns:
        Dict[str, str]: Dictionary with traceparent and tracestate
    """
    carrier = {}
    inject(TraceContextTextMapPropagator(), carrier, get_current())
    return carrier

@contextmanager
def create_span(
    operation_name: str,
    attributes: Dict[str, Any] = None,
    context: Context = None,
    kind: SpanKind = SpanKind.CLIENT,
    session_id: str = None,
    deduplicate: bool = True,
    link_to_current: bool = True
):
    """
    Create a span with the given operation name and attributes.
    
    Args:
        operation_name: Name of the operation being traced
        attributes: Dictionary of span attributes
        context: Optional parent context
        kind: Kind of span (default: CLIENT)
        session_id: Optional session ID for tracking
        deduplicate: Whether to deduplicate identical spans
        link_to_current: Whether to link to the current span
        
    Yields:
        The created span
    """
    global _current_spans
    
    # If telemetry is not initialized, just yield a dummy span
    if not tracer:
        class DummySpan:
            def set_attribute(self, *args, **kwargs): pass
            def set_attributes(self, *args, **kwargs): pass
            def record_exception(self, *args, **kwargs): pass
            def set_status(self, *args, **kwargs): pass
            def add_event(self, *args, **kwargs): pass
            def set_output(self, *args, **kwargs): pass
            def get_span_context(self): 
                class DummyContext:
                    def __init__(self):
                        self.span_id = 0
                return DummyContext()
        yield DummySpan()
        return
    
    # If no attributes provided, create empty dict
    if attributes is None:
        attributes = {}
    
    # Add session ID if provided
    if session_id and SpanAttributes.SESSION_ID not in attributes:
        attributes[SpanAttributes.SESSION_ID] = session_id
    
    # Check for duplicate spans if deduplication is enabled
    if deduplicate:
        span_key = f"{operation_name}:{session_id}"
        if span_key in _current_spans:
            # Use existing span
            yield _current_spans[span_key]
            return
    
    # Ensure we capture the current span as parent if available
    if link_to_current and context is None:
        current_span = trace.get_current_span()
        if current_span and hasattr(current_span, 'get_span_context'):
            current_context = current_span.get_span_context()
            if hasattr(current_context, 'is_valid') and current_context.is_valid:
                # Use current context to ensure proper parent-child relationship
                context = trace.set_span_in_context(current_span)
    
    # Start the span with the tracer
    with tracer.start_as_current_span(
        operation_name,
        context=context,
        kind=kind,
        attributes=attributes
    ) as span:
        # Register the span in our registry
        from opentelemetry.trace import format_span_id
        span_id = format_span_id(span.get_span_context().span_id)
        _current_spans[span_id] = span
        
        # Store span for deduplication if needed
        if deduplicate and session_id:
            span_key = f"{operation_name}:{session_id}"
            _current_spans[span_key] = span
            
        # Get QA ID if present in attributes
        qa_id = attributes.get(SpanAttributes.QA_ID)
        
        # Register span for feedback association if session_id and qa_id are present
        if session_id and qa_id and 'feedback' not in operation_name.lower():
            # Get span ID for registration
            # Import here to avoid circular imports
            from .spans import register_span
            register_span(session_id, qa_id, span_id)
        
        # Add specialized output setter method (for Phoenix UI)
        if not hasattr(span, "set_output"):
            def set_output(output):
                try:
                    # Try to use OpenInference's native set_output if available
                    from openinference.instrumentation import get_current_span
                    openinference_span = get_current_span()
                    if openinference_span and hasattr(openinference_span, "set_output"):
                        openinference_span.set_output(output)
                    # Always set our own attributes as a fallback
                    if isinstance(output, str):
                        span.set_attribute("output.value", output)
                        # Add the OpenInference compatible attribute 
                        span.set_attribute("openinference.llm.output", output)
                    elif isinstance(output, dict):
                        span.set_attribute("output", json.dumps(output))
                        # Add individual attributes for dict elements
                        for key, value in output.items():
                            if isinstance(value, (str, int, float, bool)):
                                span.set_attribute(f"output.{key}", value)
                except Exception as e:
                    # If anything fails, at least set the output value attribute
                    logger.warning(f"Error in set_output: {e}")
                    if isinstance(output, str):
                        span.set_attribute("output.value", output)
                    elif isinstance(output, dict):
                        span.set_attribute("output", json.dumps(output))
            span.set_output = set_output
            
        try:
            yield span
        except Exception as e:
            # Record exception on span
            span.record_exception(e)
            span.set_status(Status(StatusCode.ERROR, str(e)))
            raise
        finally:
            # Remove span from registry when it's completed to prevent memory leaks
            if span_id in _current_spans:
                del _current_spans[span_id]
            
            # Clean up span reference if deduplication was used
            if deduplicate and session_id:
                span_key = f"{operation_name}:{session_id}"
                if span_key in _current_spans:
                    del _current_spans[span_key]

def create_trace_span(carrier=None, default_session_id=None, operation_name="api_request", kind=SpanKind.SERVER):
    """
    Create a span with the appropriate trace context.
    Returns the span directly instead of using a context manager.
    
    Args:
        carrier: Dictionary containing traceparent and tracestate, or request object
        default_session_id: Default session ID to use if not found in carrier
        operation_name: Name for the span
        kind: Kind of span (default: SERVER)
        
    Returns:
        A tuple (span, session_id, qa_id) or (None, default_session_id, None) if tracer not available
    """
    if tracer is None:
        return None, default_session_id, None
    
    # Extract trace context from carrier
    context = extract_trace_context(carrier)
    
    # Extract session ID and QA ID
    session_id, qa_id = extract_session_info(carrier)
    
    # Use default session ID if not found
    if not session_id:
        session_id = default_session_id
    
    # Prepare attributes
    attributes = {}
    if session_id:
        attributes[SpanAttributes.SESSION_ID] = session_id
    if qa_id:
        attributes[SpanAttributes.QA_ID] = qa_id
    
    # Create the span
    span = tracer.start_span(
        operation_name,
        context=context,
        kind=kind,
        attributes=attributes
    )
    
    return span, session_id, qa_id

def validate_config(config: Dict[str, Any], schema: Dict[str, Any], path: str = "") -> Tuple[Dict[str, Any], List[str]]:
    """
    Validate a configuration dictionary against a schema.
    
    Args:
        config: Configuration dictionary to validate
        schema: Schema dictionary defining the expected structure
        path: Current path in the schema (for nested validation)
        
    Returns:
        Tuple[Dict[str, Any], List[str]]: Validated config and list of validation errors
    """
    validated = {}
    errors = []
    
    # Check if config is None or not a dictionary
    if config is None:
        errors.append(f"{path}: Configuration is None")
        return {}, errors
    
    if not isinstance(config, dict):
        errors.append(f"{path}: Configuration is not a dictionary")
        return {}, errors
    
    # Validate each field in the schema
    for field, field_schema in schema.items():
        field_path = f"{path}.{field}" if path else field
        field_type = field_schema.get("type")
        required = field_schema.get("required", False)
        
        # Check if required field is missing
        if required and (field not in config or config[field] is None):
            errors.append(f"{field_path}: Required field is missing")
            continue
        
        # Skip validation if field is not present and not required
        if field not in config:
            continue
        
        value = config[field]
        
        # Validate field type
        if field_type and not isinstance(value, field_type):
            errors.append(f"{field_path}: Expected type {field_type.__name__}, got {type(value).__name__}")
            continue
        
        # Handle nested schema validation
        if field_type == dict and "schema" in field_schema:
            nested_schema = field_schema["schema"]
            nested_validated, nested_errors = validate_config(value, nested_schema, field_path)
            validated[field] = nested_validated
            errors.extend(nested_errors)
        else:
            validated[field] = value
    
    return validated, errors

def get_span_by_id(span_id: str) -> Optional[Span]:
    """
    Attempt to retrieve an active span by its ID.
    
    This is a best-effort function that may not work for all spans, especially
    if the span has been completed/ended.
    
    Args:
        span_id: The span ID to look for
        
    Returns:
        Optional[Span]: The span if found, None otherwise
    """
    # Check if OpenTelemetry is initialized
    if not tracer:
        logger.warning("Cannot get span by ID: telemetry not initialized")
        return None
    
    try:
        # Get current active span if available
        current_span = trace.get_current_span()
        if current_span:
            # Format the current span's ID
            from opentelemetry.trace import format_span_id
            current_span_id = format_span_id(current_span.get_span_context().span_id)
            
            # If this is the span we're looking for, return it
            if current_span_id == span_id:
                return current_span
        
        # Check if the span is in our registry
        # This is basically a fallback and may not work in all cases
        # as OTEL doesn't provide native support for looking up spans by ID
        global _current_spans
        if span_id in _current_spans:
            return _current_spans.get(span_id)
            
        logger.warning(f"Span with ID {span_id} not found")
        return None
    except Exception as e:
        logger.error(f"Error retrieving span by ID: {e}")
        return None

# Initialize telemetry at import time
telemetry_initialized = initialize_telemetry(service_name="ATLAS")
