"""
Telemetry module for Phoenix Arize integration.

This module centralizes all telemetry-related functionality for the ATLAS application,
providing consistent interfaces for trace context propagation, span creation,
and attribute management.
"""

import os
import logging
import datetime
from typing import Dict, Any, Optional, List, Tuple, Union, ContextManager
from contextlib import contextmanager
import random
import time

# OpenTelemetry imports
from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode, SpanKind, Span
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator
from phoenix.otel import register

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Span attribute constants
class SpanAttributes:
    """Constants for span attribute names to ensure consistency."""
    # Session and request identifiers
    SESSION_ID = "session_id"
    QA_ID = "qa_id"
    INPUT_VALUE = "input.value"
    CHAT_HISTORY_LENGTH = "chat_history_length"
    
    # Model and configuration
    LLM_MODEL = "llm_model"
    EMBEDDING_MODEL = "embedding.model"
    RETRIEVAL_SEARCH_TYPE = "retrieval.search_type"
    RETRIEVAL_ALGORITHM = "retrieval.algorithm"
    RETRIEVAL_K = "retrieval.k"
    RETRIEVAL_SCORE_THRESHOLD = "retrieval.score_threshold"
    RETRIEVAL_FETCH_K = "retrieval.fetch_k"
    RETRIEVAL_CITATION_LIMIT = "retrieval.citation_limit"
    CHUNKING_SIZE = "chunking.size"
    CHUNKING_OVERLAP = "chunking.overlap"
    INDEX_NAME = "index.name"
    DATABASE_TYPE = "database.type"
    
    # Target configuration
    TEST_TARGET = "test_target"
    TEST_TARGET_PREFIX = "target."
    
    # Response metrics
    TIMESTAMP = "timestamp"
    RESPONSE_LENGTH = "response_length"
    DOCUMENT_COUNT = "document_count"
    FETCH_K = "fetch_k"
    CITATION_COUNT = "citation_count"
    CITATION_LIMIT = "citation_limit"
    CHUNK_COUNT = "chunk_count"
    
    # Query analysis
    QUERY_FOCUS = "query_focus"
    DETECTED_CONTEXTS = "detected_contexts"
    METADATA_CONSTRAINTS = "metadata_constraints"
    IS_STREAMING = "is_streaming"
    REQUEST_STRUCTURED_CITATIONS = "request_structured_citations"
    
    # Environment
    PROJECT = "project"
    ENVIRONMENT = "environment"
    SERVICE = "service"
    TEST_TYPE = "test_type"
    
    # Feedback attributes
    FEEDBACK_ANSWER_RATING = "feedback.answer_rating"
    FEEDBACK_CITATIONS_RATING = "feedback.citations_rating"
    FEEDBACK_TEXT = "feedback_text"
    TARGET_SPAN_ID = "target_span_id"

# Global tracer provider and tracer
tracer_provider = None
tracer = None

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
    phoenix_api_key = os.getenv('PHOENIX_API_KEY', '')
    if not phoenix_api_key and os.getenv('PHOENIX_CLIENT_HEADERS', ''):
        # Try extracting API key from PHOENIX_CLIENT_HEADERS if PHOENIX_API_KEY isn't set
        headers = os.getenv('PHOENIX_CLIENT_HEADERS', '')
        if 'api_key=' in headers:
            phoenix_api_key = headers.split('api_key=')[1].split(',')[0].strip()
            logger.info("Extracted API key from PHOENIX_CLIENT_HEADERS")

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
        # Check if we have a valid API key
        if not phoenix_api_key:
            logger.error("No Phoenix API key found in environment variables")
            return False
            
        logger.info(f"Initializing Phoenix connection for project: {phoenix_project_name}")
        
        # Register the tracer provider with Phoenix
        headers = {"api_key": phoenix_api_key}
        
        tracer_provider = register(
            project_name=phoenix_project_name,
            endpoint=phoenix_collector_endpoint,
            headers=headers,
        )
        
        # Get a tracer from the provider
        tracer = trace.get_tracer(service_name or __name__)
        
        # Create a test span to verify connectivity
        with tracer.start_as_current_span("phoenix_connection_test") as span:
            span.set_attribute(SpanAttributes.PROJECT, phoenix_project_name)
            span.set_attribute(SpanAttributes.ENVIRONMENT, os.getenv('OTEL_RESOURCE_ATTRIBUTES'))
            span.set_attribute(SpanAttributes.SERVICE, os.getenv('OTEL_SERVICE_NAME'))
            span.set_attribute(SpanAttributes.TEST_TYPE, "connection_verification")
            span.set_attribute(SpanAttributes.TIMESTAMP, datetime.datetime.utcnow().isoformat())
            span.set_status(Status(StatusCode.OK))
            span.add_event("This is a test span to verify Phoenix connectivity")
        
        logger.info(f"✅ Successfully initialized Phoenix tracing for project: {phoenix_project_name}")
        return True
    except Exception as e:
        logger.error(f"❌ Failed to initialize Phoenix tracing: {e}", exc_info=True)
        tracer = None
        return False

def extract_trace_context(carrier: Any) -> Optional[trace.Context]:
    """
    Extract trace context from a carrier object (request, dict, etc.)
    
    Args:
        carrier: Object containing trace context (request, dict, etc.)
        
    Returns:
        Optional[trace.Context]: Extracted trace context or None if not found
    """
    if not carrier:
        return None
    
    traceparent = None
    tracestate = None
    
    try:
        # If carrier is a Flask request object
        if hasattr(carrier, 'headers'):
            traceparent = carrier.headers.get('traceparent')
            tracestate = carrier.headers.get('tracestate', '')
            
            # Also check JSON body
            if hasattr(carrier, 'json'):
                try:
                    json_data = carrier.json
                    trace_context = json_data.get('trace_context', {})
                    if trace_context:
                        traceparent = traceparent or trace_context.get('traceparent')
                        tracestate = tracestate or trace_context.get('tracestate', '')
                except Exception as json_error:
                    logger.warning(f"Could not extract JSON from request: {json_error}")
        
        # If carrier is a dictionary (e.g., from Socket.IO)
        elif isinstance(carrier, dict):
            # Check for trace_context dictionary
            trace_context = carrier.get('trace_context', {})
            if trace_context:
                traceparent = trace_context.get('traceparent')
                tracestate = trace_context.get('tracestate', '')
            else:
                # Direct access if not in trace_context
                traceparent = carrier.get('traceparent')
                tracestate = carrier.get('tracestate', '')
        
        # Extract context if we have a traceparent
        if traceparent and traceparent.startswith('00-'):
            propagator = TraceContextTextMapPropagator()
            carrier_dict = {'traceparent': traceparent}
            if tracestate:
                carrier_dict['tracestate'] = tracestate
                
            return propagator.extract(carrier=carrier_dict)
    except Exception as extract_error:
        logger.warning(f"Error extracting trace context: {extract_error}")
    
    return None

def extract_session_info(carrier: Any) -> Tuple[str, Optional[str]]:
    """
    Extract session ID and QA ID from a carrier object.
    
    Args:
        carrier: Object containing session information
        
    Returns:
        Tuple[str, Optional[str]]: Session ID and QA ID (or None if not found)
    """
    session_id = "unknown"
    qa_id = None
    
    try:
        # If carrier is a Flask request object
        if hasattr(carrier, 'headers'):
            session_id = carrier.headers.get('X-Session-ID', session_id)
            qa_id = carrier.headers.get('X-QA-ID')
            
            # Also check JSON body
            if hasattr(carrier, 'json'):
                try:
                    json_data = carrier.json
                    if 'session_id' in json_data:
                        session_id = json_data.get('session_id', session_id)
                    if 'qa_id' in json_data:
                        qa_id = qa_id or json_data.get('qa_id')
                except Exception:
                    pass
        
        # If carrier is a dictionary (e.g., from Socket.IO)
        elif isinstance(carrier, dict):
            if 'session_id' in carrier:
                session_id = carrier.get('session_id', session_id)
            if 'qa_id' in carrier:
                qa_id = carrier.get('qa_id')
    except Exception as e:
        logger.warning(f"Error extracting session info: {e}")
    
    return session_id, qa_id

def inject_trace_context() -> Dict[str, str]:
    """
    Inject the current trace context into a carrier dictionary.
    
    Returns:
        Dict[str, str]: Dictionary with traceparent and tracestate
    """
    carrier = {}
    try:
        propagator = TraceContextTextMapPropagator()
        propagator.inject(carrier)
    except Exception as e:
        logger.warning(f"Error injecting trace context: {e}")
    
    return {
        "traceparent": carrier.get("traceparent", ""),
        "tracestate": carrier.get("tracestate", "")
    }

@contextmanager
def create_span(
    operation_name: str,
    attributes: Dict[str, Any] = None,
    context: trace.Context = None,
    kind: SpanKind = SpanKind.SERVER,
    session_id: str = None,
    deduplicate: bool = True
) -> ContextManager[Optional[Span]]:
    """
    Create a span with the given name and attributes.
    
    Args:
        operation_name: Name of the span
        attributes: Dictionary of attributes to add to the span
        context: Optional trace context to use
        kind: Kind of span (default: SERVER to ensure spans appear in Phoenix UI)
        session_id: Optional session ID to include in span name for deduplication
        deduplicate: Whether to check for and prevent duplicate spans (default: True)
        
    Yields:
        Span or None if tracer is not available
    """
    if not tracer:
        logger.warning(f"Phoenix tracer not available - cannot create span '{operation_name}'")
        try:
            yield None
        finally:
            pass
        return
    
    # If session_id is provided, create a more specific operation name
    # This helps with deduplication and debugging
    if session_id:
        full_operation_name = f"{operation_name}.{session_id}"
    else:
        full_operation_name = operation_name
    
    # Check for potential duplicate spans if deduplication is enabled
    if deduplicate:
        current_span = trace.get_current_span()
        if current_span and hasattr(current_span, "name") and current_span.name == full_operation_name:
            # If we already have a span with this name, reuse it to avoid duplication
            logger.debug(f"Reusing existing span: {full_operation_name}")
            try:
                yield current_span
            finally:
                pass
            return
    
    try:
        # Ensure attributes dictionary exists
        if attributes is None:
            attributes = {}
            
        # Add session_id to attributes if provided and not already present
        if session_id and SpanAttributes.SESSION_ID not in attributes:
            attributes[SpanAttributes.SESSION_ID] = session_id
            
        # Add timestamp if not already present
        if SpanAttributes.TIMESTAMP not in attributes:
            attributes[SpanAttributes.TIMESTAMP] = datetime.datetime.utcnow().isoformat()
        
        with tracer.start_as_current_span(
            full_operation_name, 
            context=context,
            kind=kind,
            attributes=attributes
        ) as span:
            yield span
    except Exception as e:
        logger.warning(f"Error creating span '{full_operation_name}': {e}")
        try:
            yield None
        finally:
            pass

def create_trace_span(carrier=None, default_session_id=None, operation_name="api_request", kind=SpanKind.SERVER):
    """
    Create a span with the appropriate trace context.
    Returns the span directly instead of using a context manager.
    
    Args:
        carrier: Dictionary containing traceparent and tracestate, or request object
        default_session_id: Session ID to use if not found in carrier
        operation_name: Name for the span operation
        kind: SpanKind to use for the span (default: SERVER)
        
    Returns:
        A tuple (span, session_id, qa_id) or (None, default_session_id, None) if tracer not available
    """
    if not tracer:
        logger.warning("Phoenix tracer not available - cannot create trace span")
        return None, default_session_id or "unknown", None
    
    # Extract session information
    session_id, qa_id = extract_session_info(carrier)
    if default_session_id and session_id == "unknown":
        session_id = default_session_id
    
    # Extract trace context
    context = extract_trace_context(carrier)
    
    # Check if we already have an active span with the same operation name and session_id
    # This helps prevent duplicate spans
    current_span = trace.get_current_span()
    if current_span and hasattr(current_span, "name") and current_span.name == operation_name:
        # If the current span has the same operation name, we might be creating a duplicate
        logger.debug(f"Detected potential duplicate span: {operation_name}. Reusing current span.")
        # Return the current span to avoid duplication
        return current_span, session_id, qa_id
    
    # Create the span
    try:
        if context:
            span = tracer.start_span(operation_name, context=context, kind=kind)
        else:
            span = tracer.start_span(operation_name, kind=kind)
        
        # Set common attributes
        span.set_attribute(SpanAttributes.SESSION_ID, session_id)
        if qa_id:
            span.set_attribute(SpanAttributes.QA_ID, qa_id)
        span.set_attribute(SpanAttributes.TIMESTAMP, datetime.datetime.utcnow().isoformat())
        
        return span, session_id, qa_id
    except Exception as e:
        logger.warning(f"Error creating trace span: {e}")
        return None, session_id, qa_id

def log_session_config(session_id: str, config_data: Dict[str, Any] = None):
    """
    Log the current configuration to Phoenix for experimental tracking.
    This function captures comprehensive test target configuration data to allow
    analysis of telemetry data by test target.
    
    Args:
        session_id: Session ID for the configuration
        config_data: Optional dictionary of configuration data
    """
    if not tracer:
        logger.warning("Phoenix tracer not available - cannot log session config")
        return
    
    # Generate a unique operation name that includes the session ID to prevent duplicates
    operation_name = f"atlas.session.configuration.{session_id}"
    
    # Check if we already have a configuration span for this session
    # This helps prevent duplicate configuration spans for the same session
    current_span = trace.get_current_span()
    if current_span and hasattr(current_span, "name") and current_span.name == operation_name:
        logger.info(f"Configuration already logged for session {session_id}, skipping duplicate")
        return
    
    if config_data is None:
        config_data = {}
    
    # Add configuration data from environment variables
    config_data.update({
        SpanAttributes.ENVIRONMENT: os.getenv('OTEL_RESOURCE_ATTRIBUTES'),
        SpanAttributes.SERVICE: os.getenv('OTEL_SERVICE_NAME'),
        SpanAttributes.TIMESTAMP: datetime.datetime.utcnow().isoformat(),
        SpanAttributes.TEST_TARGET: os.getenv('TEST_TARGET', 'unknown')
    })
    
    # Add environment variables with ATLAS_ prefix for test configuration
    atlas_env_vars = {}
    for key, value in os.environ.items():
        if key.startswith('ATLAS_'):
            # Strip ATLAS_ prefix for cleaner attribute names
            clean_key = key[6:].lower()  # Remove 'ATLAS_' and convert to lowercase
            atlas_env_vars[clean_key] = value
    
    # Add atlas environment variables to config_data with proper prefix
    if atlas_env_vars:
        config_data['atlas_env_vars'] = atlas_env_vars
    
    # Try to import test target configuration
    test_target_name = os.getenv('TEST_TARGET', 'unknown')
    test_target_data = {}
    
    if test_target_name != 'unknown':
        try:
            import importlib
            import sys
            
            # Extract the module name from the full path if it includes 'backend.targets'
            if test_target_name.startswith('backend.targets.'):
                # Remove the 'backend.' prefix as we're already in the backend directory
                test_target_name = test_target_name[8:]

            # First try direct import
            try:
                test_module = importlib.import_module(test_target_name)
            except ImportError:
                # If that fails, try with targets prefix
                try:
                    test_module = importlib.import_module(f"targets.{test_target_name.split('.')[-1]}")
                except ImportError:
                    # Try to import the nested module structure (module_name/module_name.py pattern)
                    try:
                        module_name = test_target_name.split('.')[-1]
                        test_module = importlib.import_module(f"targets.{module_name}.{module_name}")
                    except ImportError:
                        # If that fails too, try to find any module in the targets directory
                        import glob
                        import os.path
                        
                        # Get the base directory of the application
                        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                        targets_dir = os.path.join(base_dir, 'targets')
                        
                        # Look for any Python files that match the test_target_name
                        potential_modules = glob.glob(f"{targets_dir}/**/*{test_target_name}*.py", recursive=True)
                        
                        if potential_modules:
                            # Take the first match and convert path to module name
                            module_path = potential_modules[0].replace(base_dir, '').replace('/', '.').replace('\\', '.')
                            if module_path.startswith('.'):
                                module_path = module_path[1:]
                            if module_path.endswith('.py'):
                                module_path = module_path[:-3]
                            
                            test_module = importlib.import_module(module_path)
                        else:
                            raise ImportError(f"No target configuration module found for {test_target_name}")
            
            # Extract all uppercase variables as configuration
            for attr_name in dir(test_module):
                if attr_name.isupper():
                    attr_value = getattr(test_module, attr_name)
                    # Use the TEST_TARGET_PREFIX from SpanAttributes
                    clean_attr_name = attr_name.lower()
                    test_target_data[clean_attr_name] = attr_value
            
            # Add test target data to config_data
            if test_target_data:
                config_data['test_target'] = test_target_data
                
            logger.info(f"Loaded target configuration from {test_target_name}")
        except Exception as e:
            logger.warning(f"Could not load test target config: {e}")
    
    # Cache the configuration data for this session
    # This allows us to associate it with all subsequent events in this session
    cache_session_config(session_id, config_data)
    
    try:
        # Create span attributes with session ID to help with deduplication
        span_attributes = {
            SpanAttributes.SESSION_ID: session_id,
            SpanAttributes.TIMESTAMP: datetime.datetime.utcnow().isoformat(),
            "event.name": "session_configuration",
            "event.domain": "atlas",
            SpanAttributes.TEST_TARGET: test_target_name
        }
        
        # Create a span for the configuration data using a consistent INTERNAL kind
        with tracer.start_as_current_span(operation_name, kind=SpanKind.INTERNAL, attributes=span_attributes) as span:
            # Process and add all configuration data as span attributes
            _add_config_to_span(span, config_data)
            
            span.set_status(Status(StatusCode.OK))
            logger.info(f"Successfully logged configuration to Phoenix for session {session_id}")
    except Exception as e:
        logger.error(f"Failed to log configuration to Phoenix: {e}", exc_info=True)

def log_user_feedback(session_id, qa_id, feedback_data):
    """
    Log user feedback as annotations to the original call_model span.
    
    This function finds the call_model span associated with the qa_id and adds
    user feedback as annotations directly to that span, following the Phoenix
    annotation pattern for proper visibility in the UI.
    
    Args:
        session_id: The session identifier
        qa_id: The unique identifier for the question/answer pair
        feedback_data: Dictionary containing feedback information:
            - answer_rating: Numeric rating for the answer quality (1-5)
            - citations_rating: Numeric rating for citation quality (1-5)
            - feedback_text: Optional text feedback
            - question: The original question
            - answer: The answer being rated
            - citations: List of citations used in the answer
            - span_id: Optional span ID to associate feedback with (if already known)
    
    Returns:
        bool: True if feedback was successfully logged, False otherwise
    """
    if not tracer:
        logger.warning("Phoenix tracer not available - cannot log user feedback")
        return False
        
    # Extract feedback components
    answer_rating = feedback_data.get('answer_rating')
    citations_rating = feedback_data.get('citations_rating')
    feedback_text = feedback_data.get('feedback_text', '')
    citations = feedback_data.get('citations', [])
    span_id = feedback_data.get('span_id', None)  # Allow explicit span ID to be passed
    
    logger.info(f"Processing feedback for qa_id={qa_id}, session_id={session_id}, "  
                f"answer_rating={answer_rating}, citations_rating={citations_rating}")
    
    # Get the target span ID for the question/answer interaction
    # This span is what we'll annotate with the feedback
    if not span_id:
        span_id = find_qa_span_id(session_id, qa_id)
        if span_id:
            logger.info(f"Found span ID {span_id} for qa_id {qa_id} to annotate with feedback")
        else:
            # If we can't find the span ID, we'll try to get the current span
            # as a fallback, but this may not be the right one
            span_id = get_current_span_id()
            if span_id:
                logger.warning(f"Could not find specific span ID for qa_id {qa_id}, "  
                             f"using current span {span_id} as fallback")
            else:
                logger.warning(f"Could not find any span ID for feedback with qa_id {qa_id}")
                return False  # Cannot proceed without a span ID
    
    # Store this span ID in environment variables for future reference
    # This helps with linking future feedback to the same span
    try:
        if span_id:
            os.environ[f"ATLAS_FEEDBACK_SPAN_ID_{qa_id}"] = span_id
            # Create a file-based cache as a fallback
            cache_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".span_cache")
            os.makedirs(cache_dir, exist_ok=True)
            cache_file = os.path.join(cache_dir, f"{qa_id}_feedback.span")
            with open(cache_file, "w") as f:
                f.write(span_id)
    except Exception as e:
        logger.warning(f"Error storing feedback span ID: {e}")
    
    # Format the ratings and prepare annotations
    annotations = []
    
    # Add answer rating annotation if provided
    if answer_rating is not None:
        annotations.append({
            "span_id": span_id,
            "name": "answer_quality",
            "annotator_kind": "HUMAN",
            "result": {
                "label": str(answer_rating),  # Use the numeric value as label to preserve scale
                "score": float(answer_rating),  # Ensure it's a float as Phoenix expects
                "explanation": f"User rated answer quality as {answer_rating}/5"
            },
            "metadata": {
                "qa_id": qa_id,
                "session_id": session_id,
                "feedback_type": "answer_rating"
            }
        })
    
    # Add citations rating annotation if provided
    if citations_rating is not None:
        annotations.append({
            "span_id": span_id,
            "name": "citation_quality",
            "annotator_kind": "HUMAN",
            "result": {
                "label": str(citations_rating),
                "score": float(citations_rating),
                "explanation": f"User rated citation quality as {citations_rating}/5"
            },
            "metadata": {
                "qa_id": qa_id,
                "session_id": session_id,
                "citation_count": len(citations) if citations else 0,
                "feedback_type": "citations_rating"
            }
        })
    
    # Add text feedback as a separate annotation if provided
    if feedback_text:
        annotations.append({
            "span_id": span_id,
            "name": "user_comments",
            "annotator_kind": "HUMAN",
            "result": {
                "label": "feedback",
                "explanation": feedback_text
            },
            "metadata": {
                "qa_id": qa_id,
                "session_id": session_id,
                "feedback_type": "text_feedback"
            }
        })
    
    # Only proceed if we have at least one annotation to send
    if not annotations:
        logger.warning("No feedback annotations to send")
        return False
        
    # Send annotations to Phoenix
    try:
        # Get Phoenix API key
        phoenix_api_key = os.getenv('PHOENIX_API_KEY', '')
        if not phoenix_api_key and os.getenv('PHOENIX_CLIENT_HEADERS', ''):
            # Try extracting API key from PHOENIX_CLIENT_HEADERS if PHOENIX_API_KEY isn't set
            headers = os.getenv('PHOENIX_CLIENT_HEADERS', '')
            if 'api_key=' in headers:
                phoenix_api_key = headers.split('api_key=')[1].split(',')[0].strip()
                
        if not phoenix_api_key:
            logger.error("No Phoenix API key found in environment variables - cannot send annotations")
            return False
            
        # Get Phoenix endpoint
        phoenix_endpoint = os.getenv('PHOENIX_ENDPOINT', 'https://app.phoenix.arize.com')
        if not phoenix_endpoint.endswith('/v1/span_annotations'):
            phoenix_endpoint = f"{phoenix_endpoint}/v1/span_annotations?sync=false"
            
        # Prepare headers with API key
        headers = {'api_key': phoenix_api_key}
        
        # Send each annotation as a separate request
        import httpx
        client = httpx.Client(timeout=10.0)
        
        all_successful = True
        for annotation in annotations:
            # Prepare payload with single annotation
            payload = {"data": [annotation]}
            
            # Send request
            response = client.post(
                phoenix_endpoint,
                json=payload,
                headers=headers
            )
            
            if response.status_code in [200, 201, 202]:
                logger.info(f"Successfully sent {annotation['name']} annotation to Phoenix for span {span_id}")
            else:
                all_successful = False
                logger.error(f"Failed to send {annotation['name']} annotation to Phoenix: {response.status_code} - {response.text}")
        
        return all_successful
    except Exception as e:
        logger.error(f"Error sending feedback annotations: {e}", exc_info=True)
        return False

def record_exception(span: Optional[Span], exception: Exception):
    """
    Record an exception in a span.
    
    Args:
        span: Span to record the exception in
        exception: Exception to record
    """
    if not span:
        return
    
    try:
        span.record_exception(exception)
        span.set_status(Status(StatusCode.ERROR, str(exception)))
    except Exception as e:
        logger.warning(f"Error recording exception: {e}")

def _get_session_config(session_id):
    """
    Retrieve the configuration data for a session.
    
    This helper function attempts to find the configuration data that was
    previously logged for a session, allowing it to be associated with
    subsequent events like feedback.
    
    Args:
        session_id: The session identifier
        
    Returns:
        dict: Configuration data for the session, or empty dict if not found
    """
    # This is a simplified implementation that would need to be expanded
    # in a production system to actually retrieve the configuration from storage
    
    # For now, we'll create a basic configuration with environment variables
    # that should be consistent with what was logged in log_session_config
    config = {
        SpanAttributes.ENVIRONMENT: os.getenv('OTEL_RESOURCE_ATTRIBUTES'),
        SpanAttributes.SERVICE: os.getenv('OTEL_SERVICE_NAME'),
        SpanAttributes.TEST_TARGET: os.getenv('TEST_TARGET', 'unknown')
    }
    
    # Try to import test target configuration for this session
    try:
        from modules.retriever import (
            LLM, EMBEDDING_MODEL, DATABASE_URL, SEARCH_TYPE,
            SEARCH_KWARGS, INDEX_NAME, ALGORITHM, CHUNK_SIZE, CHUNK_OVERLAP
        )
        
        # Add retriever configuration
        config.update({
            SpanAttributes.LLM_MODEL: getattr(LLM, 'model_name', getattr(LLM, 'model', str(LLM))),
            SpanAttributes.EMBEDDING_MODEL: EMBEDDING_MODEL,
            SpanAttributes.RETRIEVAL_SEARCH_TYPE: SEARCH_TYPE,
            SpanAttributes.RETRIEVAL_ALGORITHM: ALGORITHM,
            SpanAttributes.RETRIEVAL_K: int(SEARCH_KWARGS.get("k", 3)),
            SpanAttributes.RETRIEVAL_SCORE_THRESHOLD: float(SEARCH_KWARGS.get("score_threshold", 0.0)),
            SpanAttributes.RETRIEVAL_FETCH_K: int(SEARCH_KWARGS.get("fetch_k", SEARCH_KWARGS.get("k", 3))),
            SpanAttributes.RETRIEVAL_CITATION_LIMIT: int(SEARCH_KWARGS.get("citation_limit", SEARCH_KWARGS.get("k", 3))),
            SpanAttributes.CHUNKING_SIZE: CHUNK_SIZE,
            SpanAttributes.CHUNKING_OVERLAP: CHUNK_OVERLAP,
            SpanAttributes.INDEX_NAME: INDEX_NAME
        })
    except ImportError:
        logger.warning(f"Could not import retriever configuration for session {session_id}")
    
    return config

# Session configuration cache to store and retrieve configuration data
# This allows us to associate configuration with all events in a session
_session_config_cache = {}

def cache_session_config(session_id, config_data):
    """
    Cache the configuration data for a session for later use.
    
    This function stores the configuration data in memory so it can be
    associated with subsequent events in the same session.
    
    Args:
        session_id: The session identifier
        config_data: Dictionary of configuration data
    """
    global _session_config_cache
    if session_id and config_data:
        _session_config_cache[session_id] = config_data.copy()
        logger.debug(f"Cached configuration for session {session_id}")

def get_cached_session_config(session_id):
    """
    Retrieve cached configuration data for a session.
    
    Args:
        session_id: The session identifier
        
    Returns:
        dict: Configuration data for the session, or None if not found
    """
    global _session_config_cache
    return _session_config_cache.get(session_id)

def _add_config_to_span(span, config_data, prefix=''):
    """
    Helper function to recursively add configuration data to a span.
    Handles nested dictionaries by flattening them with dot notation.
    
    Args:
        span: The span to add attributes to
        config_data: Dictionary of configuration data
        prefix: Prefix for attribute keys (used for recursive calls)
    """
    for key, value in config_data.items():
        # Determine the full attribute key with prefix
        if prefix:
            attr_key = f"{prefix}.{key}"
        else:
            # Use appropriate prefix based on key type for top-level keys
            if key == 'test_target':
                attr_key = SpanAttributes.TEST_TARGET_PREFIX.rstrip('.')
            elif key == 'atlas_env_vars':
                attr_key = 'env'
            elif key.startswith("target.") or key.startswith("env.") or key.startswith("config."):
                attr_key = key
            else:
                attr_key = f"config.{key}"
        
        # Handle different value types
        if isinstance(value, dict):
            # Recursively process nested dictionaries
            _add_config_to_span(span, value, attr_key)
        elif isinstance(value, (list, tuple)):
            # Convert lists to strings but limit length
            if len(value) > 0:
                if all(isinstance(item, (str, int, float, bool)) for item in value):
                    # For simple types, join with commas
                    list_str = str(value)
                    if len(list_str) > 1000:  # Limit very long lists
                        list_str = list_str[:997] + "..."
                    span.set_attribute(attr_key, list_str)
                else:
                    # For complex types, just indicate it's a list with length
                    span.set_attribute(attr_key, f"[List with {len(value)} items]")
            else:
                span.set_attribute(attr_key, "[]")
        elif isinstance(value, (str, int, float, bool)):
            # Primitive types can be added directly
            span.set_attribute(attr_key, value)
        else:
            # Convert other types to strings but limit length
            str_value = str(value)
            if len(str_value) > 1000:  # Limit very long strings
                str_value = str_value[:997] + "..."
            span.set_attribute(attr_key, str_value)

def cleanup_span_cache():
    """
    Clean up old span cache files to prevent unlimited accumulation.
    Removes files older than SPAN_CACHE_MAX_AGE and ensures the total 
    number of files doesn't exceed SPAN_CACHE_MAX_FILES.
    """
    try:
        cache_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".span_cache")
        if not os.path.exists(cache_dir):
            return
            
        # Get all files in the cache directory with their modification times
        files = []
        for filename in os.listdir(cache_dir):
            file_path = os.path.join(cache_dir, filename)
            if os.path.isfile(file_path):
                mtime = os.path.getmtime(file_path)
                files.append((file_path, mtime))
                
        # Remove files older than the maximum age
        now = time.time()
        for file_path, mtime in files:
            if now - mtime > SPAN_CACHE_MAX_AGE:
                try:
                    os.remove(file_path)
                    logger.debug(f"Removed old span cache file: {file_path}")
                except Exception as e:
                    logger.warning(f"Failed to remove old span cache file {file_path}: {e}")
                    
        # If we still have too many files, remove the oldest ones
        files = [f for f in files if os.path.exists(f[0])]  # Filter out already removed files
        if len(files) > SPAN_CACHE_MAX_FILES:
            # Sort by modification time (oldest first)
            files.sort(key=lambda x: x[1])
            # Remove oldest files until we're under the limit
            for file_path, _ in files[:len(files) - SPAN_CACHE_MAX_FILES]:
                try:
                    os.remove(file_path)
                    logger.debug(f"Removed excess span cache file: {file_path}")
                except Exception as e:
                    logger.warning(f"Failed to remove excess span cache file {file_path}: {e}")
    except Exception as e:
        logger.warning(f"Error during span cache cleanup: {e}")

# Maximum age of span cache files in seconds (7 days)
SPAN_CACHE_MAX_AGE = 7 * 24 * 60 * 60

# Maximum number of files in the span cache directory
SPAN_CACHE_MAX_FILES = 1000

def find_qa_span_id(session_id: str, qa_id: str) -> Optional[str]:
    """
    Attempt to find the span ID associated with a specific question/answer interaction.
    
    This function tries to identify the span related to a qa_id by:
    1. Looking for spans with matching qa_id attribute
    2. Looking for parent spans of the current context
    3. Looking for call_model spans which are likely parents of the Q&A interaction
    4. Checking environment variables and file-based cache for stored span IDs
    
    Args:
        session_id: The session identifier
        qa_id: The unique identifier for the question/answer pair
        
    Returns:
        Optional[str]: The span ID if found, None otherwise
    """
    try:
        # Periodically clean up the span cache
        # Only run cleanup approximately 1% of the time to avoid overhead
        if random.random() < 0.01:
            cleanup_span_cache()
            
        # Check if we stored the span_id in an environment variable or another global state
        # This approach requires ensuring the span_id is saved during call_model execution
        logger.info(f"Looking for span ID for qa_id: {qa_id} and session_id: {session_id}")
        
        # Try to get the current span and trace context
        from opentelemetry.trace import get_current_span, get_tracer_provider, SpanKind
        
        # If we're using Phoenix, try to find the span in active spans
        current_span = get_current_span()
        if current_span:
            # If the current span has qa_id attribute matching our qa_id, use that span
            span_context = current_span.get_span_context() if hasattr(current_span, "get_span_context") else None
            if span_context:
                # Check if this span matches our qa_id
                if hasattr(current_span, "attributes"):
                    span_qa_id = current_span.attributes.get(SpanAttributes.QA_ID)
                    if span_qa_id == qa_id:
                        logger.info(f"Found matching span ID for qa_id {qa_id} in current span context")
                        from opentelemetry.trace import format_span_id
                        return format_span_id(span_context.span_id)
                    
                    # Check if this is a call_model span, which would be the parent we want to annotate
                    span_name = getattr(current_span, "name", "")
                    span_kind = current_span.attributes.get("span.kind", "")
                    is_call_model = span_name == "call_model" or "call_model" in span_name
                    is_server_span = span_kind == "SERVER" or current_span.kind == SpanKind.SERVER
                    
                    if is_call_model and is_server_span:
                        logger.info(f"Found call_model span with ID {format_span_id(span_context.span_id)}")
                        from opentelemetry.trace import format_span_id
                        return format_span_id(span_context.span_id)
        
        # Look for environment variables that might have been set
        # This helps bridge the gap between API call and original request
        import os
        env_var_qa_id = f"ATLAS_SPAN_ID_{qa_id}"
        env_var_call_model = f"ATLAS_CALL_MODEL_SPAN_ID_{qa_id}"
        env_var_session_id = f"ATLAS_SPAN_ID_{session_id}"
        
        if env_var_call_model in os.environ:
            span_id = os.environ[env_var_call_model]
            logger.info(f"Found span ID {span_id} in environment variable {env_var_call_model}")
            return span_id
        
        if env_var_qa_id in os.environ:
            span_id = os.environ[env_var_qa_id]
            logger.info(f"Found span ID {span_id} in environment variable {env_var_qa_id}")
            return span_id
        
        if env_var_session_id in os.environ:
            span_id = os.environ[env_var_session_id]
            logger.info(f"Found span ID {span_id} in environment variable {env_var_session_id}")
            return span_id
        
        # Check file-based cache if environment variables don't have the span ID
        # This is especially useful in environments where env vars don't persist between requests
        try:
            cache_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".span_cache")
            cache_file = os.path.join(cache_dir, f"{qa_id}.span")
            if os.path.exists(cache_file):
                with open(cache_file, "r") as f:
                    span_id = f.read().strip()
                    if span_id:
                        logger.info(f"Found span ID {span_id} in cache file {cache_file}")
                        # Store in environment variable for faster access next time
                        os.environ[env_var_qa_id] = span_id
                        os.environ[env_var_call_model] = span_id
                        return span_id
        except Exception as e:
            logger.warning(f"Error reading span ID from cache file: {e}")
            
    except Exception as e:
        logger.warning(f"Error trying to find qa span ID: {e}")
    
    # If all else fails, return None and let the caller decide what to do
    logger.warning(f"Could not find span ID for qa_id: {qa_id} and session_id: {session_id}")
    return None

def get_current_span_id() -> Optional[str]:
    """
    Get the ID of the current span in the OpenTelemetry context.
    
    Returns:
        Optional[str]: The formatted span ID or None if there is no current span
    """
    try:
        from opentelemetry.trace import format_span_id, get_current_span
        
        span = get_current_span()
        if span and hasattr(span, "get_span_context"):
            span_context = span.get_span_context()
            if span_context and hasattr(span_context, "span_id"):
                return format_span_id(span_context.span_id)
    except Exception as e:
        logger.error(f"Error getting current span ID: {e}")
    
    return None

def send_annotation_to_phoenix(span_id: str, ratings: dict, explanation: str = "", metadata: Dict[str, Any] = None) -> bool:
    """
    Send an annotation to Phoenix to attach feedback to a specific span.
    
    Args:
        span_id: The ID of the span to annotate
        ratings: Dictionary with rating values (answer_rating, citations_rating)
        explanation: Optional explanation for the feedback
        metadata: Optional additional metadata to include with the annotation
        
    Returns:
        bool: True if the annotation was successfully sent, False otherwise
    """
    if not span_id:
        logger.warning("Cannot send annotation without a span_id")
        return False
        
    # Get configuration from environment variables
    phoenix_api_key = os.getenv('PHOENIX_API_KEY', '')
    if not phoenix_api_key and os.getenv('PHOENIX_CLIENT_HEADERS', ''):
        # Try extracting API key from PHOENIX_CLIENT_HEADERS if PHOENIX_API_KEY isn't set
        headers = os.getenv('PHOENIX_CLIENT_HEADERS', '')
        if 'api_key=' in headers:
            phoenix_api_key = headers.split('api_key=')[1].split(',')[0].strip()
            
    if not phoenix_api_key:
        logger.error("No Phoenix API key found in environment variables - cannot send annotation")
        return False
    
    # Get the original answer rating (1-5)
    answer_rating = ratings.get('answer_rating')
    
    # Prepare the annotation payload using numeric labels to preserve the Likert scale
    annotation_payload = {
        "data": [
            {
                "span_id": span_id,
                "name": "user feedback",
                "annotator_kind": "HUMAN",
                "result": {
                    # Use the numeric value as the label to preserve Likert scale
                    "label": str(answer_rating) if answer_rating is not None else "none",
                    # Include the raw score value
                    "score": answer_rating if answer_rating is not None else None,
                    "explanation": explanation
                },
                "metadata": metadata or {}
            }
        ]
    }
    
    # Add citation rating as a second annotation if available
    citations_rating = ratings.get('citations_rating')
    if citations_rating is not None:
        # Add citation feedback as a second annotation with numeric label
        annotation_payload["data"].append({
            "span_id": span_id,
            "name": "citation relevance",
            "annotator_kind": "HUMAN",
            "result": {
                # Use the numeric value as the label to preserve Likert scale
                "label": str(citations_rating),
                # Include the raw score
                "score": citations_rating,
                "explanation": f"Citation relevance rating: {citations_rating}/5"
            },
            "metadata": metadata or {}
        })
    
    # Prepare headers with API key
    headers = {'api_key': phoenix_api_key}
    
    # Get Phoenix endpoint from environment or use default
    phoenix_endpoint = os.getenv('PHOENIX_ENDPOINT', 'https://app.phoenix.arize.com')
    if not phoenix_endpoint.endswith('/v1/span_annotations'):
        phoenix_endpoint = f"{phoenix_endpoint}/v1/span_annotations?sync=false"
    
    try:
        # Send the annotation to Phoenix
        import httpx
        client = httpx.Client(timeout=10.0)  # Set a reasonable timeout
        response = client.post(
            phoenix_endpoint,
            json=annotation_payload,
            headers=headers
        )
        
        if response.status_code in [200, 201, 202]:
            logger.info(f"Successfully sent annotation to Phoenix for span {span_id}")
            return True
        else:
            logger.error(f"Failed to send annotation to Phoenix: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        logger.error(f"Error sending annotation to Phoenix: {e}")
        return False
