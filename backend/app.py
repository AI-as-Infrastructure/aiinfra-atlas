import logging
import os
import datetime
import uuid

# Import OpenTelemetry modules for Phoenix integration
from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode, SpanKind
from openinference.instrumentation import using_session
from contextlib import contextmanager

# Keep LangChain instrumentation for model observability
from openinference.instrumentation.langchain import LangChainInstrumentor

# Import centralized telemetry module
from modules.telemetry import (
    initialize_telemetry, create_trace_span, create_span, 
    log_session_config, extract_trace_context, inject_trace_context,
    SpanAttributes, tracer, log_user_feedback
)

from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_socketio import SocketIO
from gevent import monkey
from asgiref.sync import async_to_sync
from gevent import spawn

# Patch sockets for gevent. Should be set to False if Nginx is handling HTTPS.
monkey.patch_all(ssl=False)

from modules.retriever import call_model  # call_model is async
from modules.system_prompts import system_prompt

# Import tools for citation enhancement
from pydantic import BaseModel, Field
from typing import List, Optional

# Citation models for structured output
class Citation(BaseModel):
    """Model for structured citations in ATLAS format."""
    source_id: str = Field(..., description="Unique identifier of the source document")
    quote: str = Field(..., description="The exact text quoted from the source")
    title: Optional[str] = Field(None, description="Title of the source document")
    url: Optional[str] = Field(None, description="URL to the full document if available")
    page_number: Optional[int] = Field(None, description="Page number if applicable")

class CitedAnswer(BaseModel):
    """Answer with citations in structured format."""
    answer: str = Field(..., description="The answer to the user's question")
    citations: List[Citation] = Field(..., description="List of citations that support the answer")

# Initialize Socket.IO without attaching it to an app
socketio = SocketIO(cors_allowed_origins="*", async_mode="gevent", logger=True, engineio_logger=True)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize OpenTelemetry with Phoenix
telemetry_initialized = initialize_telemetry(service_name=__name__)

# Initialize LangChain instrumentation to capture model calls
if telemetry_initialized:
    LangChainInstrumentor().instrument()
    logger.info("✅ Successfully initialized Phoenix tracing and LangChain instrumentation")
else:
    logger.warning("⚠️ Phoenix tracing not initialized - telemetry will be disabled")

def create_trace_span(carrier=None, default_session_id=None, operation_name="api_request"):
    """
    Create a span with the appropriate trace context.
    Returns the span directly instead of using a context manager.
    
    Args:
        carrier: Dictionary containing traceparent and tracestate, or request object
        default_session_id: Session ID to use if not found in carrier
        operation_name: Name for the span operation
        
    Returns:
        A tuple (span, session_id, qa_id) or (None, default_session_id, None) if tracer not available
    """
    if not tracer:
        logger.warning("Phoenix tracer not available - cannot create trace span")
        return None, default_session_id, None
    
    # Initialize variables
    session_id = default_session_id or "unknown"
    qa_id = None
    context = None
    traceparent = None
    tracestate = None
    
    try:
        # Extract context information from carrier
        if carrier:
            # If carrier is a Flask request object
            if hasattr(carrier, 'headers'):
                traceparent = carrier.headers.get('traceparent')
                tracestate = carrier.headers.get('tracestate', '')
                session_id = carrier.headers.get('X-Session-ID', session_id)
                qa_id = carrier.headers.get('X-QA-ID')
                
                # Also check JSON body
                if hasattr(carrier, 'json'):
                    try:
                        json_data = carrier.json
                        trace_context = json_data.get('trace_context', {})
                        if trace_context:
                            traceparent = traceparent or trace_context.get('traceparent')
                            tracestate = tracestate or trace_context.get('tracestate', '')
                        
                        # Get session_id and qa_id from JSON if not in headers
                        if 'session_id' in json_data:
                            session_id = json_data.get('session_id', session_id)
                        if 'qa_id' in json_data:
                            qa_id = qa_id or json_data.get('qa_id')
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
                
                # Get session_id and qa_id
                if 'session_id' in carrier:
                    session_id = carrier.get('session_id', session_id)
                if 'qa_id' in carrier:
                    qa_id = carrier.get('qa_id')
        
        # Extract context if we have a traceparent
        if traceparent and traceparent.startswith('00-'):
            try:
                propagator = TraceContextTextMapPropagator()
                carrier_dict = {'traceparent': traceparent}
                if tracestate:
                    carrier_dict['tracestate'] = tracestate
                    
                context = propagator.extract(carrier=carrier_dict)
            except Exception as extract_error:
                logger.warning(f"Error extracting trace context: {extract_error}")
                
        # Create the span
        if context:
            span = tracer.start_span(operation_name, context=context, kind=SpanKind.SERVER)
        else:
            span = tracer.start_span(operation_name, kind=SpanKind.SERVER)
        
        # Add attributes to span
        span.set_attribute("session_id", session_id)
        if qa_id:
            span.set_attribute("qa_id", qa_id)
            
        return span, session_id, qa_id
                
    except Exception as e:
        logger.error(f"Error creating trace span: {e}", exc_info=True)
        return None, session_id, qa_id

# Use the centralized log_session_config function from telemetry module
# This function has been moved to modules/telemetry.py

def create_app():
    app = Flask(__name__)
    
    # Get environment configuration
    environment = os.environ.get('ENVIRONMENT', 'dev').lower()  # New environment toggle
    server_name = os.environ.get('SERVER_NAME', 'localhost')
    host = os.environ.get('HOST', server_name)
    
    # Determine allowed origins based on environment
    allowed_origins = []
    
    # Always include API URLs from environment variables if available
    api_url_dev = os.environ.get('API_URL_DEV')
    api_url_staging = os.environ.get('API_URL_STAGING')
    api_url_prod = os.environ.get('API_URL_PROD')
    
    if api_url_dev:
        allowed_origins.append(api_url_dev)
    if api_url_staging:
        allowed_origins.append(api_url_staging)
    if api_url_prod:
        allowed_origins.append(api_url_prod)
    
    # Add environment-specific frontend URLs
    if environment == 'dev':
        # Development environment
        allowed_origins.extend([
            'https://localhost:3001',
            'http://localhost:3001'
        ])
    else:
        # Staging/Production environment
        # Add both HTTP and HTTPS variants with the server_name
        allowed_origins.extend([
            f'https://{server_name}',
            f'http://{server_name}',
            f'https://{server_name}:3001',
            f'http://{server_name}:3001'
        ])
        
        # If host is different from server_name, add it too
        if host != server_name:
            allowed_origins.extend([
                f'https://{host}',
                f'http://{host}',
                f'https://{host}:3001',
                f'http://{host}:3001'
            ])
    
    # Add any explicit IPs from API_URL_STAGING if it contains an IP
    if api_url_staging and ('192.168.' in api_url_staging or '10.' in api_url_staging):
        ip = api_url_staging.split('//')[1].split(':')[0]
        allowed_origins.extend([
            f'https://{ip}',
            f'http://{ip}',
            f'https://{ip}:3001',
            f'http://{ip}:3001'
        ])
        
    # Add any explicit IPs from API_URL_PROD if it contains an IP
    if api_url_prod and ('192.168.' in api_url_prod or '10.' in api_url_prod):
        ip = api_url_prod.split('//')[1].split(':')[0]
        allowed_origins.extend([
            f'https://{ip}',
            f'http://{ip}',
            f'https://{ip}:3001',
            f'http://{ip}:3001'
        ])
    
    # Configure CORS with the determined origins
    CORS(app, origins=allowed_origins)
    
    # Initialize logger (moved before using it)
    logger = logging.getLogger(__name__)
    
    # Log the environment and allowed origins for debugging
    logger.info(f"Environment: {environment}")
    logger.info(f"CORS allowed origins: {allowed_origins}")
    
    # Attach Socket.IO to the app
    socketio.init_app(app)

    from modules.retriever import (
        get_retriever, call_model, State,
        LLM, EMBEDDING_MODEL, DATABASE_URL, SEARCH_TYPE,
        SEARCH_KWARGS, INDEX_NAME, ALGORITHM, CHUNK_SIZE,
        CHUNK_OVERLAP, system_prompt
    )

    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    logger = logging.getLogger(__name__)
    logger.debug(
        f"Loaded environment variables: LLM={LLM}, EMBEDDING_MODEL={EMBEDDING_MODEL}, DATABASE_URL={DATABASE_URL}, "
        f"SEARCH_TYPE={SEARCH_TYPE}, SEARCH_KWARGS={SEARCH_KWARGS}, INDEX_NAME={INDEX_NAME}, ALGORITHM={ALGORITHM}, "
        f"CHUNK_SIZE={CHUNK_SIZE}, CHUNK_OVERLAP={CHUNK_OVERLAP}, SYSTEM_PROMPT={system_prompt}"
    )

    # Helper function for enhancing citations with additional metadata
    def enhance_citations(sources):
        """Enhance citation data with additional metadata if available"""
        enhanced_sources = []
        
        for source in sources:
            # Create a copy of the source to avoid modifying the original
            enhanced_source = {**source}
            
            # Ensure we have a title
            if not enhanced_source.get('title') and enhanced_source.get('metadata', {}).get('title'):
                enhanced_source['title'] = enhanced_source['metadata']['title']
            
            # Try to extract a quote if not present but content is available
            if not enhanced_source.get('quote') and enhanced_source.get('content'):
                # Take first 150 characters as a default quote
                enhanced_source['quote'] = enhanced_source['content'][:150] + '...' if len(enhanced_source['content']) > 150 else enhanced_source['content']
            
            # Ensure we have a URL if possible
            if not enhanced_source.get('url') and enhanced_source.get('metadata', {}).get('source'):
                enhanced_source['url'] = enhanced_source['metadata']['source']
            
            enhanced_sources.append(enhanced_source)
        
        return enhanced_sources

    # Add Socket.IO handler for session reset
    @socketio.on("session_reset")
    def handle_session_reset(data):
        session_id = data.get("session_id")
        logger.info(f"Session reset requested for: {session_id}")
        socketio.emit("session_reset_confirmed", {"session_id": session_id})

    @socketio.on("session_start")
    def handle_session_start(data):
        session_id = data.get("session_id")
        logger.info(f"New session started: {session_id}")
        
        # Extract any additional config data from the request
        config_data = data.get("config_data", {})
        
        # Import retriever configuration for logging
        try:
            from modules.retriever import (
                LLM, EMBEDDING_MODEL, DATABASE_URL, SEARCH_TYPE,
                SEARCH_KWARGS, INDEX_NAME, ALGORITHM, CHUNK_SIZE, CHUNK_OVERLAP
            )
            
            # Add retriever configuration to config_data using SpanAttributes constants
            retriever_config = {
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
                SpanAttributes.INDEX_NAME: INDEX_NAME,
                SpanAttributes.DATABASE_TYPE: DATABASE_URL.split(':')[0] if ':' in DATABASE_URL else 'unknown',
                "experiment.citation_ranking_enabled": False,
                "experiment.context_detection_enabled": True,
                "experiment.metadata_filtering_enabled": True,
                SpanAttributes.TEST_TARGET: os.getenv('TEST_TARGET', 'unknown')
            }
            
            # Update config_data with retriever configuration
            config_data.update(retriever_config)
        except ImportError as e:
            logger.warning(f"Could not import retriever configuration: {e}")
        
        # Log configuration data using the centralized function
        log_session_config(session_id, config_data)
        
        socketio.emit("session_started", {
            "session_id": session_id,
            "status": "active"
        })

    @socketio.on("feedback")
    def handle_feedback(data):
        try:
            session_id = data.get("session_id")
            qa_id = data.get("qa_id")  # Unique ID for this specific Q&A pair
            question = data.get("question")
            answer = data.get("answer")
            answer_rating = data.get("answer_rating")
            citations_rating = data.get("citations_rating")
            feedback_text = data.get("feedback_text")
            citations = data.get("citations", [])
            sources = data.get("sources", [])

            logger.info(f"Received feedback for session {session_id}, qa_id {qa_id}: rating={answer_rating}, feedback={feedback_text}")

            # Log user feedback to Phoenix with human role tag
            from modules.telemetry import log_user_feedback
            
            # Prepare feedback data dictionary
            feedback_data = {
                "question": question,
                "answer": answer,
                "answer_rating": answer_rating,
                "citations_rating": citations_rating,
                "feedback_text": feedback_text,
                "citations": citations
            }
            
            # Use the specialized feedback logging function
            success = log_user_feedback(session_id, qa_id, feedback_data)
            
            if success:
                logger.info(f"Successfully logged feedback to Phoenix for session {session_id}, qa_id {qa_id}")
            else:
                logger.warning(f"Failed to log feedback to Phoenix for session {session_id}, qa_id {qa_id}")

            socketio.emit("feedback_confirmed", {
                "session_id": session_id,
                "qa_id": qa_id,
                "status": "success"
            })

        except Exception as e:
            logger.error(f"Error processing feedback: {e}", exc_info=True)
            socketio.emit("feedback_error", {
                "session_id": data.get("session_id", "unknown"),
                "qa_id": data.get("qa_id", None),
                "error": str(e)
            })

    @app.route('/api/config', methods=['GET'])
    def config():
        # Truncate system prompt if it's too long
        max_prompt_length = 150  # Characters to show before truncating
        truncated_prompt = system_prompt
        if len(system_prompt) > max_prompt_length:
            truncated_prompt = system_prompt[:max_prompt_length] + "..."
        
        llm_model_name = getattr(LLM, 'model_name', getattr(LLM, 'model', str(LLM)))
        config_data = {
            "LLM": llm_model_name,
            "EMBEDDING_MODEL": EMBEDDING_MODEL,
            "DATABASE_URL": DATABASE_URL.split('@')[1] if '@' in DATABASE_URL else DATABASE_URL,  # Hide credentials
            "SEARCH_TYPE": SEARCH_TYPE,
            "SEARCH_KWARGS": SEARCH_KWARGS,
            "INDEX_NAME": INDEX_NAME,
            "ALGORITHM": ALGORITHM,
            "CHUNK_SIZE": CHUNK_SIZE,
            "CHUNK_OVERLAP": CHUNK_OVERLAP,
            "SYSTEM_PROMPT": truncated_prompt,
            "FULL_SYSTEM_PROMPT": system_prompt  # Add the full prompt as a new field
        }
        logger.debug(f"Config Data: {config_data}")
        return jsonify(config_data)

    @app.route('/api/ask', methods=['POST'])
    def ask():
        try:
            data = request.json
            question = data.get('question')
            chat_history = data.get('chat_history', [])
            # Use provided session_id or generate a new one.
            session_id = data.get('session_id') or str(uuid.uuid4())
            qa_id = data.get('qa_id') or f"qa_{uuid.uuid4()}"
            cognito_id = data.get('cognito_id')
            session_type = data.get('session_type', 'single')  # Default to single session type

            logger.debug(f"Received data: {data}")

            if not question:
                return jsonify({"error": "No 'question' provided."}), 400

            # Check if this is a new session (empty chat history)
            is_new_session = not chat_history
            
            if is_new_session:
                # Log configuration data for new sessions
                log_session_config(session_id)

            # Create a span for this request
            span, trace_session_id, trace_qa_id = create_trace_span(request, session_id, "atlas.api.ask")
            
            try:
                # Maintain state for streaming; call_model will update state with the answer.
                # Note: Citation re-ranking has been backed out in favor of basic selection in retriever.py.
                state = {
                    "input": question,
                    "chat_history": chat_history,
                    "context": "",
                    "answer": "",
                    "question": question,
                    "session_id": session_id,
                    "qa_id": qa_id,
                    "request_structured_citations": True,  # Flag to request structured citations
                    "trace_context": data.get('trace_context')  # Pass trace context to call_model
                }

                # Use gevent to spawn the async call in a separate greenlet
                # This prevents issues with interpreter shutdown
                spawn(lambda: async_to_sync(call_model)(state, socketio))

                if span:
                    span.set_status(Status(StatusCode.OK))
                return jsonify({"status": "streaming initiated", "session_id": session_id, "qa_id": qa_id})
            finally:
                # End the span
                if span:
                    span.end()
                    
        except Exception as e:
            logger.error(f"Error in /api/ask: {e}", exc_info=True)
            return jsonify({"error": "Internal Server Error"}), 500

    # Socket.IO event handler for processing sources and improving citations
    @socketio.on("response")
    def handle_response(data):
        if data.get("sources"):
            # Enhance sources with better metadata
            enhanced_sources = enhance_citations(data["sources"])
            # Update the data with enhanced sources
            data["sources"] = enhanced_sources
            # Log citation enhancement
            logger.debug(f"Enhanced {len(enhanced_sources)} citations with additional metadata")
            
    # Socket.IO event: When the answer is complete, log to Phoenix
    @socketio.on("finalize_qa")
    def finalize_qa(data):
        """
        Expected data:
          {
            "session_id": <session_id>,
            "qa_id": <qa_id>,
            "answer": <final answer string>,
            "citations": <list of citations>,
            "trace_context": <trace context object>
          }
        """
        session_id = data.get("session_id")
        answer = data.get("answer", "")
        citations = data.get("citations", [])
        qa_id = data.get("qa_id", f"qa_{uuid.uuid4()}")
        question = data.get("question", "")
        trace_context = data.get("trace_context", {})
        
        logger.debug(f"Received finalize_qa for session_id: {session_id} with answer length {len(answer)}")
        
        # Create a span for this finalization
        span, _, _ = create_trace_span(data, session_id, "atlas.qa.finalize")
        
        try:
            # Enhance citations with better metadata if possible
            if citations:
                citations = enhance_citations(citations)
                
            logger.info(f"Logging finalized QA to Phoenix for session {session_id}, qa_id {qa_id}")
            
            # Log the finalized answer to Phoenix, tagged as LLM.
            try:
                # Create span attributes with appropriate values
                qa_attributes = {
                    SpanAttributes.SESSION_ID: session_id,
                    SpanAttributes.QA_ID: qa_id,
                    SpanAttributes.INPUT_VALUE: question,
                    SpanAttributes.OUTPUT_VALUE: answer,
                    SpanAttributes.CITATION_COUNT: len(citations),
                    SpanAttributes.TIMESTAMP: datetime.datetime.utcnow().isoformat(),
                    "role": "LLM"
                }
                
                # Only include condensed citation info to avoid span size issues
                if citations:
                    citation_ids = [c.get('id', 'unknown') for c in citations if isinstance(c, dict)]
                    qa_attributes["citation_ids"] = str(citation_ids)
                    
                    corpus_counts = {}
                    for c in citations:
                        if isinstance(c, dict) and c.get('corpus'):
                            corpus = c.get('corpus')
                            corpus_counts[corpus] = corpus_counts.get(corpus, 0) + 1
                    qa_attributes["corpus_distribution"] = str(corpus_counts)
                
                # Use the create_span function from telemetry module
                with create_span("atlas.llm.response", attributes=qa_attributes, kind=SpanKind.PRODUCER) as qa_span:
                    if qa_span:
                        qa_span.set_status(Status(StatusCode.OK))
                        
                logger.info(f"Successfully logged finalize_qa to Phoenix for session {session_id}")
            except Exception as phoenix_error:
                logger.error(f"Failed to log finalize_qa to Phoenix: {phoenix_error}")
                
            # Notify client that the QA has been finalized
            socketio.emit("qa_updated", {
                "status": "updated", 
                "session_id": session_id,
                "qa_id": qa_id,
                "enhanced_citations": citations  # Send enhanced citations back to the client
            })
            logger.info(f"Finalized QA for session {session_id}")
            
            if span:
                span.set_status(Status(StatusCode.OK))
        except Exception as e:
            logger.error(f"Error finalizing QA for session {session_id}: {e}", exc_info=True)
            if span:
                span.record_exception(e)
                span.set_status(Status(StatusCode.ERROR, str(e)))
        finally:
            # End the span
            if span:
                span.end()

    @socketio.on("connect")
    def handle_connect():
        logger.info("Socket.IO client connected.")

    @socketio.on("disconnect")
    def handle_disconnect():
        logger.info("Socket.IO client disconnected.")

    @socketio.on("message")
    def handle_message(data):
        session_id = data.get("session_id", "unknown")
        question = data.get("question", "")
        if not question or not question.strip():
            logger.error(f"[Session {session_id}] No valid question received.")
            socketio.emit("response", {"message": "No valid question received."})
            return

        logger.info(f"[Session {session_id}] Received message: {question}")

        try:
            state = {
                "input": question,
                "chat_history": data.get("chat_history", []),
                "context": "",
                "answer": "",
                "question": question,
                "session_id": session_id,
                "request_structured_citations": True  # Flag to request structured citations
            }
            async_to_sync(call_model)(state, socketio)
        except Exception as e:
            logger.error(f"[Session {session_id}] Error during Socket.IO message handling: {e}", exc_info=True)
            socketio.emit("response", {"message": "An error occurred while processing your request."})

    return app, socketio

if __name__ == '__main__':
    # Import secrets manager to access configuration
    from utils.secrets_manager import get_secret
    
    app, socketio = create_app()
    port = int(get_secret('PORT', 5000))
    # Always bind to all interfaces (0.0.0.0) to make the app accessible from Docker containers
    host = '0.0.0.0'
    socketio.run(app, host=host, port=port, debug=True)