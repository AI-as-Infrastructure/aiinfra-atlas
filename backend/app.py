import os

from fastapi import FastAPI, HTTPException, Request, Body, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
import os
from dotenv import load_dotenv
import asyncio
import json
import datetime
import logging
from typing import Dict, List, Optional
import uuid
from fastapi.middleware.trustedhost import TrustedHostMiddleware

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables with strict mode - fail if environment file is missing
project_root = os.path.dirname(os.path.dirname(__file__))

# Get environment from ENVIRONMENT (set by deployment scripts)
atlas_environment = os.getenv("ENVIRONMENT")
if not atlas_environment:
    logger.error("ENVIRONMENT variable is not set. Cannot determine which configuration to use.")
    raise EnvironmentError("ENVIRONMENT must be set (e.g., 'development', 'staging', 'production') in your .env file")
    
env_file_name = f".env.{atlas_environment.lower()}"
env_path = os.path.join(project_root, "config", env_file_name)

# Strict checking - application will not start if the environment file is missing
if not os.path.exists(env_path):
    logger.error(f"Required environment file not found: {env_path} (ATLAS_ENV='{atlas_environment}')")
    raise FileNotFoundError(f"Cannot find environment file: {env_path}. Deployment is misconfigured.")

# Load the environment file
logger.info(f"Loading environment variables from: {env_path} (ATLAS_ENV='{atlas_environment}')")
load_dotenv(dotenv_path=env_path, override=True)
# Environment variables are now loaded directly with no need for an env_loaded flag

# Initialize telemetry after environment variables are loaded
from backend.telemetry.core import initialize_telemetry

# Get environment for telemetry behavior
environment = os.getenv("ENVIRONMENT", "development").lower()
telemetry_enabled = os.getenv("TELEMETRY_ENABLED", "true").lower() in ["true", "1", "yes"]

if not telemetry_enabled:
    logger.info("📝 Telemetry disabled via TELEMETRY_ENABLED=false")
    telemetry_success = True  # Consider disabled telemetry as "successful" for app startup
else:
    try:
        telemetry_success = initialize_telemetry()
        if telemetry_success:
            logger.info("✅ Telemetry initialized successfully")
        else:
            # When telemetry is enabled, it MUST work in ALL environments
            logger.error(f"❌ CRITICAL: Telemetry initialization failed in {environment}")
            raise RuntimeError(f"Telemetry is enabled but initialization returned False")
    except Exception as e:
        # When telemetry is enabled, failures are fatal in ALL environments
        logger.error(f"❌ CRITICAL: Telemetry initialization failed in {environment}: {e}")
        raise RuntimeError(f"Telemetry initialization failed: {e}")

# Import core modules and telemetry utilities
from backend.telemetry import (

    create_span,
    log_user_feedback,
    SpanAttributes,
    SpanNames,
    telemetry_initialized,
    telemetry_router,
    OpenInferenceSpanKind,
    Status,
    StatusCode
)

# Import our new utility modules
from backend.modules.config import (
    initialize_config, 
    get_config, 
    get_retriever, 
    get_retriever_instance,
    get_system_prompt,
    get_corpus_options,
    get_citation_limit
)
from backend.modules.document_retrieval import retrieve_documents_with_telemetry
from backend.modules.corpus_filtering import filter_documents_with_telemetry
from backend.modules.streaming import (
    format_sse_message, 
    create_error_message,
    create_complete_message,
    create_chunk_message,
    stream_response_chunks,
    stream_documents_as_references
)
from backend.modules.llm import generate_response_with_telemetry
from backend.telemetry.feedback import UserFeedback, FeedbackResponse
from backend.modules.auth import get_current_user, optional_user
from backend.modules.sensitive_contexts import detect_sensitive_contexts
from backend.telemetry.config_attrs import get_test_target_attributes

# Import async queue management
if environment in ["production", "staging"]:
    # In production/staging, Redis async queue is REQUIRED
    try:
        from backend.services.queue_manager import get_queue_manager
        async_queue_available = True
        logger.info("✅ Async queue manager imported successfully")
    except ImportError as e:
        logger.error(f"❌ CRITICAL: Async queue manager not available in {environment}: {e}")
        raise RuntimeError(f"Redis queue manager is required in {environment} but not available: {e}")
else:
    # Development environment - async queue is optional
    try:
        from backend.services.queue_manager import get_queue_manager
        async_queue_available = True
        logger.info("✅ Async queue manager imported successfully (development)")
    except ImportError as e:
        logger.warning(f"⚠️ Async queue manager not available in development: {e}")
        logger.info("📝 Development mode: continuing without Redis async queue")
        async_queue_available = False

if not telemetry_initialized:
    if not telemetry_enabled:
        logger.info("📝 Telemetry not initialized (explicitly disabled)")
    else:
        raise RuntimeError(f"Telemetry is enabled but not initialized. The app cannot start without telemetry.")

# Initialize FastAPI app
app = FastAPI(title="ATLAS")

# Configure CORS with explicit origins for development and production
# Read CORS_ORIGINS from environment and parse as list
cors_origins_env = os.environ.get("CORS_ORIGINS", "")
origins = [origin.strip() for origin in cors_origins_env.split(",") if origin.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include the telemetry router
app.include_router(telemetry_router)

# Initialize configuration
try:
    logger.info("Initializing configuration and retriever")
    initialize_config()
    logger.info("Configuration and retriever initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize configuration: {e}")
    raise

# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket, session_id: str):
        await websocket.accept()
        self.active_connections[session_id] = websocket

    def disconnect(self, session_id: str):
        if session_id in self.active_connections:
            del self.active_connections[session_id]

    async def send_message(self, session_id: str, message: dict):
        if session_id in self.active_connections:
            await self.active_connections[session_id].send_json(message)

manager = ConnectionManager()

@app.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    await manager.connect(websocket, session_id)
    
    # Import telemetry functions
    from backend.telemetry import using_session, log_user_feedback
    
    # Log WebSocket connection
    logger.info(f"WebSocket connected for session_id={session_id}")
    
    # Use the session context manager to ensure all spans are associated with this session
    with using_session(session_id):
        try:
            while True:
                # Use a timeout to prevent hanging connections
                try:
                    # Wait for a message with a timeout
                    data = await asyncio.wait_for(websocket.receive_json(), timeout=60.0)
                    
                    # Handle different message types
                    if data.get("type") == "feedback":
                        # Process feedback
                        feedback_data = data.get("data", {})
                        qa_id = feedback_data.get("qa_id")
                        feedback = feedback_data.get("feedback", {})
                        
                        # Debug logging
                        logger.info(f"Received feedback via WebSocket for session_id={session_id}, qa_id={qa_id}")
                        
                        try:
                            # Validate incoming data
                            if not qa_id or not feedback:
                                raise ValueError("Missing qa_id or feedback data")
                            
                            # Log feedback using the telemetry system
                            success = await log_user_feedback(session_id, qa_id, feedback)
                            
                            # Send confirmation
                            response = {
                                "type": "feedback_confirmed",
                                "qa_id": qa_id,
                                "success": success
                            }
                            
                            # Add error message if feedback association failed
                            if not success:
                                error_msg = "Unable to associate your feedback with this conversation. This may happen if the conversation data has expired."
                                logger.warning(f"Feedback association failed for session_id={session_id}, qa_id={qa_id}")
                                response["message"] = error_msg
                        except Exception as e:
                            logger.error(f"Error processing feedback for session_id={session_id}, qa_id={qa_id}: {e}", exc_info=True)
                            response = {
                                "type": "feedback_confirmed",
                                "qa_id": qa_id,
                                "success": False,
                                "message": "An error occurred while processing your feedback. Please try again later."
                            }
                        
                        await manager.send_message(session_id, response)
                    
                    elif data.get("type") == "ping":
                        # Handle ping and send immediate response
                        logger.debug(f"Received ping from session_id={session_id}")
                        await manager.send_message(session_id, {
                            "type": "pong",
                            "session_id": session_id
                        })
                    
                    elif data.get("type") == "reset_session":
                        # Handle session reset
                        logger.info(f"Session reset requested for session_id={session_id}")
                        await manager.send_message(session_id, {
                            "type": "session_reset_confirmed",
                            "session_id": session_id
                        })
                
                except asyncio.TimeoutError:
                    # Send a ping to check if client is still there
                    try:
                        await manager.send_message(session_id, {"type": "ping"})
                    except Exception:
                        # If we can't send a ping, the connection is probably dead
                        logger.info(f"WebSocket connection timed out for session_id={session_id}")
                        break
        
        except WebSocketDisconnect:
            logger.info(f"WebSocket disconnected for session_id={session_id}")
            manager.disconnect(session_id)
        except Exception as e:
            logger.error(f"WebSocket error for session_id={session_id}: {e}", exc_info=True)
            manager.disconnect(session_id)
        finally:
            # Clean up connection
            manager.disconnect(session_id)
            logger.info(f"WebSocket connection closed for session_id={session_id}")

# --- Health check endpoint ---
@app.get("/")
async def root():
    """Health check endpoint"""
    return {"status": "ok"}

# --- Query endpoint (non-streaming) ---
@app.post("/query")
@app.post("/api/query")  # Add an alias with /api prefix for frontend compatibility
async def query(request: Request):
    """Simple document retrieval endpoint"""
    data = await request.json()
    query = data.get("query")
    session_id = data.get("session_id")
    qa_id = data.get("qa_id")
    corpus_filter = data.get("corpus_filter", "all")
    
    if not query:
        raise HTTPException(status_code=400, detail="Query is required")
    
    # Use our document retrieval utility
    documents, qa_id = retrieve_documents_with_telemetry(
        query=query,
        retriever=get_retriever(),
        session_id=session_id,
        qa_id=qa_id,
        corpus_filter=corpus_filter
    )
    
    # Format documents as citations for frontend display
    citations = []
    for idx, doc in enumerate(documents):
        try:
            # Import the format_document_for_citation function
            from backend.retrievers.hansard_retriever import format_document_for_citation
            citation = format_document_for_citation(doc, idx)
            if citation:
                citations.append(citation)
        except Exception as e:
            logger.error(f"Error formatting document as citation: {e}")
    
    # Return both raw results and formatted citations
    return {
        "result": [doc.page_content for doc in documents],
        "qa_id": qa_id,
        "citations": citations,
        "document_count": len(documents)
    }

# --- Configuration endpoint ---
@app.get("/api/config")
def get_config_endpoint():
    """Return application configuration for UI display."""
    config = get_config()
    retriever_config = config.get("retriever_config", {})
    
    # Import the full system prompt from system_prompts
    from backend.modules.system_prompts import system_prompt_text
    
    # Build configuration for API use
    config_data = {
        "ATLAS_VERSION": config.get("ATLAS_VERSION", "1.0.0"),
        "SYSTEM_PROMPT": get_system_prompt()[:150] + "..." if len(get_system_prompt()) > 150 else get_system_prompt(),
        "FULL_SYSTEM_PROMPT": system_prompt_text,
        "CORPUS_OPTIONS": get_corpus_options(),
        
        # Include all retriever configuration
        "target_id": retriever_config.get("target_id"),
        "target_version": retriever_config.get("target_version", "1.0"),
        "embedding_model": retriever_config.get("embedding_model"),
        "search_type": retriever_config.get("search_type"),
        "search_k": retriever_config.get("search_k"),
        "search_score_threshold": retriever_config.get("search_score_threshold"),
        "pooling": retriever_config.get("pooling"),
        "citation_limit": retriever_config.get("citation_limit"),
        "LARGE_RETRIEVAL_SIZE_SINGLE_CORPUS": retriever_config.get("LARGE_RETRIEVAL_SIZE_SINGLE_CORPUS"),
        "LARGE_RETRIEVAL_SIZE_ALL_CORPUS": retriever_config.get("LARGE_RETRIEVAL_SIZE_ALL_CORPUS"),
        "algorithm": retriever_config.get("algorithm"),
        "chunk_size": retriever_config.get("chunk_size"),
        "chunk_overlap": retriever_config.get("chunk_overlap"),
        "index_name": retriever_config.get("index_name"),
        
        # Include LLM configuration
        "llm_provider": config.get("llm_provider"),
        "llm_model": config.get("llm_model"),
        
        # Include vector database info
        "composite_target": f"{retriever_config.get('target_id')}_{retriever_config.get('chroma_collection_name')}"
    }
    
    # Add extra config fields from environment variables
    config_data["MULTI_CORPUS_VECTORSTORE"] = os.getenv("MULTI_CORPUS_VECTORSTORE")
    config_data["CHROMA_COLLECTION_NAME"] = os.getenv("CHROMA_COLLECTION_NAME")
    
    return JSONResponse(content=config_data)

# --- Synchronous Q&A endpoint (non-streaming) ---
@app.post("/api/ask")
async def ask(data: dict = Body(...)):
    """
    Process a question and return a response with citations.
    This is the non-streaming version of the ask endpoint.
    """
    try:
        # Extract question and session ID from request
        question = data.get("question", "").strip()
        session_id = data.get("session_id")
        feedback = data.get("feedback")

        # Validate required fields
        if not question:
            raise ValueError("Question is required")
        if not session_id:
            raise ValueError("Session ID is required")

        # Get configuration
        config = get_config()
        if not config:
            raise ValueError("Configuration not available")

        # Process the question
        response_text, documents, qa_id = process_question(question, session_id, config)

        # Log feedback if provided
        if feedback:
            try:
                await log_user_feedback(session_id, qa_id, feedback)
            except Exception as e:
                # Log the error but don't fail the request
                logger.error(f"Error logging feedback: {e}", exc_info=True)

        return {
            "result": response_text,
            "session_id": session_id,
            "qa_id": qa_id,
            "document_count": len(documents)
        }

    except ValueError as e:
        # Handle validation errors
        logger.warning(f"Validation error in /api/ask: {e}")
        raise HTTPException(
            status_code=400,
            detail="Invalid request parameters"
        )
    except Exception as e:
        # Log the full error server-side
        logger.error(f"Error in /api/ask: {e}", exc_info=True)
        # Raise a sanitized error for the client
        raise HTTPException(
            status_code=500,
            detail="An error occurred while processing your request"
        )

# --- Streaming Q&A endpoint ---
@app.post("/api/ask/stream")
async def ask_stream(data: dict = Body(...)):
    """
    Stream an answer to a question using retrieved documents and a language model.
    """
    # Extract request data
    question = data.get("question", "")
    corpus_filter = data.get("corpus_filter", "all")
    previous_corpus_filter = data.get("previous_corpus_filter", "all")
    chat_history = data.get("chat_history", [])
    session_id = data.get("session_id", str(uuid.uuid4()))
    qa_id = data.get("qa_id", str(uuid.uuid4()))
    provider = data.get("provider", None)  # Optional LLM provider override
    
    # Import required telemetry constants
    from backend.telemetry import SpanAttributes, OpenInferenceSpanKind, SpanNames
    
    # Define async generator for streaming response
    async def response_generator():
        # Use nonlocal to access/modify the qa_id from the outer scope
        nonlocal qa_id
        
        # Create a parent span for the entire RAG pipeline
        # This allows us to track the complete operation from retrieval to generation
        from backend.telemetry import create_rag_pipeline_span
        
        # Get test target configuration for telemetry
        test_target_attrs = get_test_target_attributes()
        
        # Create base attributes for the span with flat structure (no info. prefixes)
        pipeline_attributes = {
            SpanAttributes.SESSION_ID: session_id,
            SpanAttributes.QA_ID: qa_id,
            # Don't use SpanAttributes.INPUT_VALUE since it has a dot notation that Phoenix consolidates into info
            # Instead use flat attribute names without dots
            "input": question,
            "query": question,
            "content": question,  # This is what Phoenix shows by default
            "is_streaming": True,
            "corpus_filter": corpus_filter,
            "previous_corpus_filter": previous_corpus_filter,
            "llm_provider": provider,
            # Use flat structure for OpenInference attributes
            "openinference.span.kind": OpenInferenceSpanKind.AGENT,
        }
        
        # Add all test target attributes individually with flat names
        for key, value in test_target_attrs.items():
            # Convert dot notation to underscore for flat naming
            flat_key = key.replace(".", "_")
            pipeline_attributes[flat_key] = value
        
        # Remove keys that would clash with explicit parameters in create_rag_pipeline_span
        safe_attributes = {k: v for k, v in pipeline_attributes.items() if k not in {SpanAttributes.QA_ID, "query"}}

        with create_rag_pipeline_span(
            session_id=session_id,
            qa_id=qa_id,
            query=question,
            **safe_attributes
        ) as parent_span:
            try:
                # Guardrail check: Detect sensitive contexts early in the pipeline
                sensitive_contexts = detect_sensitive_contexts(
                    query=question,
                    session_id=session_id,
                    qa_id=qa_id,
                    parent_span=parent_span  # Pass the RAG pipeline span as parent
                )
                
                # Ensure guardrail span completes before starting retrieval
                # This ensures proper span ID ordering in Phoenix UI
                await asyncio.sleep(0.001)  # 1ms delay to ensure span completion
                
                # Log if any sensitive contexts were detected
                if sensitive_contexts:
                    logger.warning(f"Detected sensitive contexts for session {session_id}: {sensitive_contexts}")
                    # In the future, this could trigger special handling, warnings, or filtering
                
                # Retrieve documents using our utility
                documents, qa_id = retrieve_documents_with_telemetry(
                    query=question,
                    retriever=get_retriever(),
                    session_id=session_id,
                    qa_id=qa_id,
                    corpus_filter=corpus_filter
                )
                
                # If no documents were retrieved, return an error
                if not documents:
                    error_msg = create_error_message(
                        "retrieval_error", 
                        "No relevant documents found for your query."
                    )
                    yield format_sse_message(error_msg, event="error")
                    return
                
                # Record document count in parent span
                parent_span.set_attribute(SpanAttributes.DOCUMENT_COUNT, len(documents))
                
                # Apply corpus filter if needed
                if corpus_filter and corpus_filter.lower() != "all":
                    from backend.modules.corpus_filtering import filter_documents_with_telemetry
                    documents = filter_documents_with_telemetry(
                        documents=documents,
                        corpus_filter=corpus_filter,
                        session_id=session_id,
                        qa_id=qa_id
                    )
                
                # Note: Document reranking is now handled directly in the HansardRetriever
                # No need for redundant reranking here
                
                # Generate and stream the response
                response_generator, qa_id = generate_response_with_telemetry(
                    question=question,
                    documents=documents,
                    session_id=session_id,
                    qa_id=qa_id,
                    chat_history=chat_history,
                    corpus_filter=corpus_filter,
                    provider=provider  # Pass the provider if specified
                )
                
                # Stream response chunks
                full_response = ""
                chunk_count = 0
                
                # Use our streaming utility to format SSE messages
                async for sse_message in stream_response_chunks(
                    chunks_generator=response_generator,
                    qa_id=qa_id,
                    session_id=session_id,
                    create_streaming_span=False  # Prevent redundant streaming spans
                ):
                    # Ensure each SSE message ends with \n\n
                    if not sse_message.endswith('\n\n'):
                        sse_message += '\n\n'
                    yield sse_message
                    await asyncio.sleep(0)
                    
                    # Extract the chunk for building full response
                    try:
                        data = json.loads(sse_message.split("data: ")[1])
                        chunk = data.get("chunk", {}).get("text", "")
                        full_response += chunk
                        chunk_count += 1
                    except (IndexError, json.JSONDecodeError):
                        pass

                # After all content, stream references/citations
                citation_limit = get_citation_limit()
                references_message = stream_documents_as_references(
                    documents=documents,
                    qa_id=qa_id,
                    session_id=session_id,
                    citation_limit=citation_limit
                )
                if not references_message.endswith('\n\n'):
                    references_message += '\n\n'
                yield references_message
                await asyncio.sleep(0)
                
                # Process the references to get citations for the parent span
                try:
                    refs_data = json.loads(references_message.split("data: ")[1])
                    all_citations = refs_data.get("allCitations", [])
                    
                    # First process the citation data we need
                    citation_summary = {
                        "count": len(all_citations),
                        "corpora": list(set(c.get("metadata", {}).get("corpus", "") for c in all_citations if "metadata" in c))
                    }
                    
                    # Create document summary before setting attributes
                    doc_summary = []
                    if all_citations:
                        for i, citation in enumerate(all_citations[:5]):
                            first_100_chars = citation.get("content", "")[:100] + "..."
                            doc_summary.append(f"Doc {i+1}: {first_100_chars}")
                    
                    # Now set the attributes all at once with flat names
                    parent_span.set_attribute("citations_json", json.dumps(all_citations))
                    parent_span.set_attribute("citations_summary", json.dumps(citation_summary))
                    
                    # Only set document summary if we have one
                    if doc_summary:
                        parent_span.set_attribute("document_summary", "\n\n".join(doc_summary))
                
                except (IndexError, json.JSONDecodeError, KeyError) as e:
                    logger.warning(f"Could not extract citations for parent span: {e}")

                # Send completion message
                complete_message = create_complete_message(
                    text=full_response,
                    qa_id=qa_id
                )
                complete_sse = format_sse_message(complete_message, event="complete")
                if not complete_sse.endswith('\n\n'):
                    complete_sse += '\n\n'
                yield complete_sse
                
                # Update parent span with final metrics
                parent_span.set_attribute(SpanAttributes.RESPONSE_LENGTH, len(full_response))
                parent_span.set_attribute("final_chunk_count", chunk_count)
                
            except Exception as e:
                # Log the full error details server-side
                logger.error(f"Error in streaming response: {e}", exc_info=True)
                # Record error in parent span
                parent_span.record_exception(e)
                parent_span.set_status(Status(StatusCode.ERROR, str(e)))
                
                # Create a sanitized error message for the client
                # Do not expose internal exception details to client
                error_msg = create_error_message(
                    "streaming_error",
                    "An error occurred while processing your request"
                )
                yield format_sse_message(error_msg, event="error")
    
    # Return the streaming response with appropriate headers
    response = StreamingResponse(response_generator(), media_type="text/event-stream")
    response.headers["Content-Type"] = "text/event-stream"
    response.headers["Cache-Control"] = "no-cache"
    response.headers["Connection"] = "keep-alive"
    response.headers["X-Accel-Buffering"] = "no"
    return response

# --- Telemetry status endpoint ---
@app.get("/api/telemetry")
def telemetry_status():
    """Return the status of telemetry (initialized or not) for health checks."""
    return {"telemetry_initialized": telemetry_initialized}

# --- Diagnostic endpoint for debugging ---
@app.get("/api/diagnostics")
async def diagnostics(request: Request):
    """Return diagnostic information to help debug issues."""
    # Check if authentication is required based on environment
    auth_required = os.getenv("VITE_USE_COGNITO_AUTH", "false").lower() == "true"
    
    if auth_required:
        # Get the authorization header
        auth_header = request.headers.get("Authorization")
        if not auth_header:
            raise HTTPException(
                status_code=401,
                detail="Authentication required for diagnostics"
            )
        
        # Verify user is authenticated
        user = await optional_user(request)
        if not user.get("authenticated", False):
            raise HTTPException(
                status_code=403,
                detail="Unauthorized access to diagnostics"
            )
    
    # Get basic config info - only non-sensitive information
    config_info = {}
    try:
        config = get_config()
        retriever_config = config.get("retriever_config", {})
        config_info = {
            "target_id": retriever_config.get("target_id"),
            "llm_provider": config.get("llm_provider"),
            "llm_model": config.get("llm_model"),
            "embedding_model": retriever_config.get("embedding_model"),
            "citation_limit": retriever_config.get("citation_limit"),
            "large_retrieval_size": retriever_config.get("large_retrieval_size"),
        }
    except Exception:
        config_info = {"error": "Configuration error occurred"}
    
    # Check critical environment variables - only return presence, not values
    env_vars = {
        "TEST_TARGET": bool(os.getenv("TEST_TARGET")),
        "REDIS_HOST": bool(os.getenv("REDIS_HOST")),
        "REDIS_PORT": bool(os.getenv("REDIS_PORT")),
        "REDIS_PASSWORD": bool(os.getenv("REDIS_PASSWORD")),
        "PHOENIX_API_KEY": bool(os.getenv("PHOENIX_API_KEY")),
        "ANTHROPIC_API_KEY": bool(os.getenv("ANTHROPIC_API_KEY")),
        "OPENAI_API_KEY": bool(os.getenv("OPENAI_API_KEY")),
    }
    
    return {
        "environment": env_vars,
        "config": config_info,
        "telemetry_initialized": telemetry_initialized
    }

# --- HTTP Feedback endpoint (fallback for WebSocket failures) ---
@app.post("/api/feedback", response_model=FeedbackResponse)
async def submit_feedback(feedback: UserFeedback, request: Request):
    """
    Submit user feedback via HTTP (fallback from WebSocket).
    This endpoint is used when WebSocket submission fails.
    """
    # Check if authentication is required based on environment
    auth_required = os.getenv("VITE_USE_COGNITO_AUTH", "false").lower() == "true"
    
    try:
        # Authentication check - only enforce in environments with auth enabled
        if auth_required:
            # Get the authorization header - will be present in HTTPS environments
            auth_header = request.headers.get("Authorization")
            
            # In production (HTTPS), we should have an auth header
            if auth_header:
                # Verify user is authenticated without recording identity
                user = await optional_user(request)
                if not user.get("authenticated", False):
                    logger.warning("Unauthenticated feedback submission attempt")
                    return FeedbackResponse(
                        message="Authentication required to submit feedback",
                        status="error"
                    )
                logger.info("Authenticated feedback submission (identity not stored)")
            else:
                # In dev environment (HTTP), we may not have auth headers for security reasons
                # Log this but allow the submission to proceed
                protocol = request.headers.get("x-forwarded-proto", "http")
                if protocol.lower() == "https":
                    # Should have auth in HTTPS but doesn't - log warning
                    logger.warning("Missing authentication for HTTPS feedback submission")
                else:
                    # Expected for HTTP development environment
                    logger.info("HTTP feedback submission without authentication (development)")
        
        client_ip = request.client.host if request.client else "unknown"
        
        # Get session ID and QA ID from the feedback
        session_id = feedback.session_id
        qa_id = feedback.qa_id
        
        # Validate session_id and qa_id
        if not session_id or not qa_id:
            logger.warning(f"Invalid feedback submission: missing session_id or qa_id")
            return FeedbackResponse(
                message="Invalid feedback submission: missing required identifiers",
                status="error"
            )
        
        # Log reception of feedback
        logger.info(f"Received HTTP feedback for session {session_id}, qa {qa_id} from {client_ip}")
        
        # Format feedback data for telemetry using the correct field names
        feedback_data = {
            "relevance": feedback.relevance,
            "factual_accuracy": feedback.factual_accuracy,
            "source_quality": feedback.source_quality,
            "clarity": feedback.clarity,
            "tags": feedback.tags,
            "feedback_text": feedback.feedback_text,
            "timestamp": feedback.timestamp or datetime.datetime.now().isoformat(),
            "source": "http_fallback",
            
            # Include rich context data from frontend
            "test_target": feedback.test_target,
            "question": feedback.question,
            "answer": feedback.answer,
            "citations": feedback.citations,
            "citation_count": len(feedback.citations) if feedback.citations else 0,
        }
        
        # Use the session context to ensure spans are properly associated
        with using_session(session_id):
            try:
                # Log user feedback
                success = await log_user_feedback(session_id, qa_id, feedback_data)
                
                if success:
                    logger.info(f"HTTP Feedback recorded for session_id={session_id}, qa_id={qa_id}")
                    return FeedbackResponse(
                        message="Feedback received successfully",
                        status="success"
                    )
                else:
                    logger.error(f"Failed to record HTTP feedback for session_id={session_id}, qa_id={qa_id}")
                    return FeedbackResponse(
                        message="Unable to associate your feedback with this conversation. This may happen if the conversation data has expired.",
                        status="error"
                    )
            except Exception as e:
                logger.error(f"Error processing HTTP feedback: {e}", exc_info=True)
                return FeedbackResponse(
                    message="Error processing feedback",
                    status="error"
                )
    except Exception as e:
        logger.error(f"Error in HTTP feedback endpoint: {e}", exc_info=True)
        return FeedbackResponse(
            message="An error occurred processing your feedback",
            status="error"
        )

# --- Security middleware for HTTPS support ---

# Allow requests only from specific hosts (prevents host header attacks)
# Get allowed hosts from CORS_ORIGINS environment variable
cors_origins = os.getenv("CORS_ORIGINS", "localhost,127.0.0.1")
allowed_hosts = [host.strip() for host in cors_origins.split(",")]

# Extract domains from URLs (remove http:// or https:// prefix if present)
allowed_hosts = [host.replace("https://", "").replace("http://", "") for host in allowed_hosts]

# Add localhost and 127.0.0.1 if not already included
if "localhost" not in allowed_hosts:
    allowed_hosts.append("localhost")
if "127.0.0.1" not in allowed_hosts:
    allowed_hosts.append("127.0.0.1")

print(f"TrustedHostMiddleware: Allowing hosts {allowed_hosts}")

app.add_middleware(
    TrustedHostMiddleware, 
    allowed_hosts=allowed_hosts
)

# Make FastAPI correctly detect HTTPS when behind Nginx proxy
@app.middleware("http")
async def handle_forwarded_proto(request: Request, call_next):
    """
    Process the X-Forwarded-Proto header to detect HTTPS correctly.
    This ensures that all URL generation and security features work properly
    when the app is behind an Nginx proxy handling HTTPS.
    """
    forwarded_proto = request.headers.get("X-Forwarded-Proto")
    if forwarded_proto:
        # Update request's scheme to the original client protocol (http/https)
        request.scope["scheme"] = forwarded_proto
    
    response = await call_next(request)
    return response

# --- Entrypoint for running with Uvicorn ---
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.app:app", host="0.0.0.0", port=8000, reload=True)

# Add this to your existing backend/app.py file
@app.get("/api/health")
def health_check():
    return {"status": "ok"}

# === ASYNC LLM REQUEST ENDPOINTS ===

@app.post("/api/ask/async")
async def ask_async(data: dict = Body(...), request: Request = None):
    """
    Submit an LLM query for async processing
    Returns immediately with a request ID for status checking
    """
    if not async_queue_available:
        raise HTTPException(
            status_code=503, 
            detail="Async processing not available. Redis queue not configured."
        )
    
    try:
        # Extract user information if available
        user_id = None
        if request:
            # Try to get user from request (adjust based on your auth system)
            try:
                user_id = getattr(request.state, 'user_id', None)
            except:
                pass
        
        # Get queue manager
        queue_manager = get_queue_manager()
        
        # Queue the request
        request_id = await queue_manager.queue_request(data, user_id)
        
        return {
            "request_id": request_id,
            "status": "queued",
            "message": "Your query has been queued for processing",
            "estimated_wait_time": "2-10 seconds"
        }
        
    except Exception as e:
        logger.error(f"Error queuing async request: {e}")
        raise HTTPException(status_code=500, detail="Failed to queue request")

@app.get("/api/ask/async/{request_id}")
async def get_async_status(request_id: str):
    """
    Get the status and result of an async LLM request
    """
    if not async_queue_available:
        raise HTTPException(
            status_code=503, 
            detail="Async processing not available. Redis queue not configured."
        )
    
    try:
        queue_manager = get_queue_manager()
        status_data = await queue_manager.get_request_status(request_id)
        
        if status_data["status"] == "not_found":
            raise HTTPException(status_code=404, detail="Request not found or expired")
        
        return status_data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting async status for {request_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get status")

@app.get("/api/queue/stats")
async def get_queue_stats():
    """
    Get current queue statistics (admin endpoint)
    """
    if not async_queue_available:
        raise HTTPException(
            status_code=503, 
            detail="Async processing not available. Redis queue not configured."
        )
    
    try:
        queue_manager = get_queue_manager()
        stats = await queue_manager.get_queue_stats()
        
        return {
            "queue_stats": stats,
            "async_enabled": True,
            "timestamp": datetime.datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting queue stats: {e}")
        raise HTTPException(status_code=500, detail="Failed to get queue stats")

@app.websocket("/ws/async/{request_id}")
async def websocket_async_status(websocket: WebSocket, request_id: str):
    """
    WebSocket endpoint for real-time async request status updates
    """
    if not async_queue_available:
        await websocket.close(code=1011, reason="Async processing not available")
        return
    
    await websocket.accept()
    
    try:
        queue_manager = get_queue_manager()
        
        # Send initial status
        initial_status = await queue_manager.get_request_status(request_id)
        await websocket.send_json(initial_status)
        
        # Poll for status updates
        while True:
            status_data = await queue_manager.get_request_status(request_id)
            
            if status_data["status"] in ["completed", "failed", "not_found"]:
                # Send final status and close
                await websocket.send_json(status_data)
                break
            
            # Wait before next poll
            await asyncio.sleep(0.5)
            
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for async request {request_id}")
    except Exception as e:
        logger.error(f"WebSocket error for async request {request_id}: {e}")
        await websocket.close(code=1011, reason="Internal server error")

@app.get("/api/vector-store-info")
async def get_vector_store_info():
    try:
        # Get the absolute path to the backend directory
        current_dir = os.path.dirname(os.path.abspath(__file__))
        file_path = os.path.join(current_dir, "targets", "blert_1000.txt")
        
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="Vector store information file not found")
        
        with open(file_path, "r") as f:
            content = f.read()
        return {"content": content}
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error")