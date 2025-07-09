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
import time
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

# WebSocket connection manager with enhanced features
class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[str, WebSocket] = {}
        self.connection_timestamps: dict[str, float] = {}
        self.connection_activity: dict[str, float] = {}  # Track last activity
        self.connection_message_counts: dict[str, int] = {}  # Track messages per connection
        
        # Configuration from environment
        self.max_connections = int(os.getenv("WEBSOCKET_MAX_CONNECTIONS", "100"))
        self.max_idle_time = int(os.getenv("WEBSOCKET_MAX_IDLE_TIME", "1800"))  # 30 minutes
        self.max_connection_time = int(os.getenv("WEBSOCKET_MAX_CONNECTION_TIME", "7200"))  # 2 hours
        self.max_messages_per_connection = int(os.getenv("WEBSOCKET_MAX_MESSAGES", "1000"))
        self.cleanup_interval = int(os.getenv("WEBSOCKET_CLEANUP_INTERVAL", "300"))  # 5 minutes
        
        # Memory monitoring
        self.memory_threshold_mb = int(os.getenv("WEBSOCKET_MEMORY_THRESHOLD_MB", "500"))
        self.last_cleanup = time.time()

    async def connect(self, websocket: WebSocket, session_id: str):
        # Check connection limits
        if len(self.active_connections) >= self.max_connections:
            await websocket.close(code=1013, reason="Server overloaded - too many connections")
            logger.warning(f"Connection rejected for {session_id}: max connections ({self.max_connections}) reached")
            return False
        
        # Check memory usage before accepting new connections
        if self._check_memory_pressure():
            await websocket.close(code=1013, reason="Server memory pressure - connection rejected")
            logger.warning(f"Connection rejected for {session_id}: memory pressure detected")
            return False
            
        await websocket.accept()
        current_time = time.time()
        self.active_connections[session_id] = websocket
        self.connection_timestamps[session_id] = current_time
        self.connection_activity[session_id] = current_time
        self.connection_message_counts[session_id] = 0
        
        logger.info(f"WebSocket connected for {session_id}. Active connections: {len(self.active_connections)}")
        
        # Perform cleanup if needed
        if current_time - self.last_cleanup > self.cleanup_interval:
            await self._background_cleanup()
            
        return True

    def disconnect(self, session_id: str):
        """Gracefully disconnect a WebSocket connection"""
        if session_id in self.active_connections:
            try:
                # Log connection statistics
                if session_id in self.connection_timestamps:
                    duration = time.time() - self.connection_timestamps[session_id]
                    messages = self.connection_message_counts.get(session_id, 0)
                    logger.info(f"WebSocket {session_id} disconnected: duration={duration:.1f}s, messages={messages}")
            except Exception as e:
                logger.error(f"Error logging disconnect stats for {session_id}: {e}")
            
            # Clean up all connection data
            del self.active_connections[session_id]
        
        # Clean up tracking data
        self.connection_timestamps.pop(session_id, None)
        self.connection_activity.pop(session_id, None)
        self.connection_message_counts.pop(session_id, None)
        
        logger.debug(f"WebSocket disconnected for {session_id}. Active connections: {len(self.active_connections)}")

    async def send_message(self, session_id: str, message: dict):
        """Send message to WebSocket with error handling and activity tracking"""
        if session_id not in self.active_connections:
            logger.warning(f"Cannot send message to {session_id}: connection not found")
            return False
            
        try:
            # Update activity and message count
            self.connection_activity[session_id] = time.time()
            self.connection_message_counts[session_id] = self.connection_message_counts.get(session_id, 0) + 1
            
            # Check if connection has exceeded message limit
            if self.connection_message_counts[session_id] > self.max_messages_per_connection:
                logger.warning(f"Connection {session_id} exceeded message limit, disconnecting")
                await self.active_connections[session_id].close(code=1008, reason="Message limit exceeded")
                self.disconnect(session_id)
                return False
            
            await self.active_connections[session_id].send_json(message)
            return True
            
        except Exception as e:
            logger.warning(f"Failed to send message to {session_id}: {e}")
            self.disconnect(session_id)
            return False

    async def _background_cleanup(self):
        """Background cleanup of stale and inactive connections"""
        current_time = time.time()
        cleanup_count = 0
        
        # Find connections to clean up
        connections_to_remove = []
        
        for session_id in list(self.active_connections.keys()):
            connection_age = current_time - self.connection_timestamps.get(session_id, current_time)
            last_activity = self.connection_activity.get(session_id, current_time)
            idle_time = current_time - last_activity
            message_count = self.connection_message_counts.get(session_id, 0)
            
            # Reasons to disconnect
            should_disconnect = False
            reason = ""
            
            if connection_age > self.max_connection_time:
                should_disconnect = True
                reason = "Maximum connection time exceeded"
            elif idle_time > self.max_idle_time:
                should_disconnect = True
                reason = "Connection idle too long"
            elif message_count > self.max_messages_per_connection:
                should_disconnect = True
                reason = "Message limit exceeded"
            
            if should_disconnect:
                try:
                    await self.active_connections[session_id].close(code=1000, reason=reason)
                except Exception as e:
                    logger.debug(f"Error closing connection {session_id}: {e}")
                
                connections_to_remove.append(session_id)
                cleanup_count += 1
        
        # Remove cleaned up connections
        for session_id in connections_to_remove:
            self.disconnect(session_id)
        
        if cleanup_count > 0:
            logger.info(f"Background cleanup: removed {cleanup_count} stale connections")
        
        self.last_cleanup = current_time

    def _check_memory_pressure(self) -> bool:
        """Check if system is under memory pressure"""
        try:
            import psutil
            memory = psutil.virtual_memory()
            # Check if available memory is less than threshold
            available_mb = memory.available / (1024 * 1024)
            if available_mb < self.memory_threshold_mb:
                logger.warning(f"Memory pressure detected: {available_mb:.1f}MB available (threshold: {self.memory_threshold_mb}MB)")
                return True
        except ImportError:
            # psutil not available, skip memory check
            pass
        except Exception as e:
            logger.error(f"Error checking memory pressure: {e}")
        
        return False

    def get_connection_stats(self) -> dict:
        """Get statistics about current connections"""
        current_time = time.time()
        stats = {
            "total_connections": len(self.active_connections),
            "max_connections": self.max_connections,
            "connections_by_age": {"0-5min": 0, "5-30min": 0, "30min+": 0},
            "connections_by_activity": {"active": 0, "idle": 0},
            "total_messages": sum(self.connection_message_counts.values()),
            "average_messages_per_connection": 0
        }
        
        if stats["total_connections"] > 0:
            stats["average_messages_per_connection"] = stats["total_messages"] / stats["total_connections"]
            
            for session_id in self.active_connections:
                # Age classification
                age = current_time - self.connection_timestamps.get(session_id, current_time)
                if age < 300:  # 5 minutes
                    stats["connections_by_age"]["0-5min"] += 1
                elif age < 1800:  # 30 minutes
                    stats["connections_by_age"]["5-30min"] += 1
                else:
                    stats["connections_by_age"]["30min+"] += 1
                
                # Activity classification
                last_activity = self.connection_activity.get(session_id, current_time)
                if current_time - last_activity < 300:  # 5 minutes
                    stats["connections_by_activity"]["active"] += 1
                else:
                    stats["connections_by_activity"]["idle"] += 1
        
        return stats

    async def cleanup_stale_connections(self):
        """Public method to trigger cleanup (for backward compatibility)"""
        await self._background_cleanup()

manager = ConnectionManager()

@app.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    connected = await manager.connect(websocket, session_id)
    if not connected:
        return
    
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
        
        # Create base attributes for the span - avoid conflicting with OpenInference input/output fields
        pipeline_attributes = {
            SpanAttributes.SESSION_ID: session_id,
            SpanAttributes.QA_ID: qa_id,
            # Store question in attributes using non-conflicting names
            "user_query": question,  # Store original question in attributes (not conflicting with input.value)
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
                
                # Step 1: HNSW retrieval with per-corpus balanced reranking
                # document_retrieval.py now handles per-corpus vs single-corpus logic internally
                # and performs balanced reranking within each corpus
                from backend.modules.config import get_search_k
                final_k = get_search_k()  # Get configured SEARCH_K (e.g., 30)
                
                documents, qa_id = retrieve_documents_with_telemetry(
                    query=question,
                    retriever=get_retriever(),
                    session_id=session_id,
                    qa_id=qa_id,
                    corpus_filter=corpus_filter,
                    k=final_k  # Use final desired document count (30 docs balanced across corpora)
                )
                
                # If no documents were retrieved, return an error
                if not documents:
                    error_msg = create_error_message(
                        "retrieval_error", 
                        "No relevant documents found for your query."
                    )
                    yield format_sse_message(error_msg, event="error")
                    return
                
                logger.info(f"📄 Retrieved {len(documents)} balanced documents (per-corpus reranked)")
                
                # Debug: Show sample content from first few reranked docs
                for i, doc in enumerate(documents[:3]):
                    content_preview = doc.page_content[:200] if hasattr(doc, 'page_content') else str(doc)[:200]
                    metadata = getattr(doc, 'metadata', {})
                    corpus = metadata.get('corpus', 'unknown')
                    logger.info(f"🥇 Reranked doc {i+1} ({corpus}): {content_preview}...")
                
                # Record final document count in parent span
                parent_span.set_attribute(SpanAttributes.DOCUMENT_COUNT, len(documents))
                
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
                
                # Set top-level span info following OpenInference conventions for proper Phoenix UI separation
                # Info field content (using OpenInference standard attributes) - same pattern as com.atlas.rag.references
                parent_span.set_attribute("input.value", question)
                parent_span.set_attribute("output.value", full_response)
                parent_span.set_attribute("openinference.span.kind", OpenInferenceSpanKind.AGENT)

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

@app.get("/api/websocket/stats")
async def websocket_stats(request: Request):
    """Return WebSocket connection statistics for monitoring."""
    # Check if authentication is required based on environment
    auth_required = os.getenv("VITE_USE_COGNITO_AUTH", "false").lower() == "true"
    
    if auth_required:
        # Get the authorization header
        auth_header = request.headers.get("Authorization")
        if not auth_header:
            raise HTTPException(
                status_code=401,
                detail="Authentication required for WebSocket stats"
            )
        
        # Verify user is authenticated
        user = await optional_user(request)
        if not user.get("authenticated", False):
            raise HTTPException(
                status_code=403,
                detail="Access denied for WebSocket stats"
            )
    
    try:
        # Get connection statistics
        stats = manager.get_connection_stats()
        
        # Add memory information if available
        try:
            import psutil
            memory = psutil.virtual_memory()
            stats["memory"] = {
                "available_mb": round(memory.available / (1024 * 1024), 1),
                "used_percent": memory.percent,
                "threshold_mb": manager.memory_threshold_mb
            }
        except ImportError:
            stats["memory"] = {"status": "psutil not available"}
        except Exception as e:
            stats["memory"] = {"error": str(e)}
        
        # Add configuration
        stats["config"] = {
            "max_connections": manager.max_connections,
            "max_idle_time": manager.max_idle_time,
            "max_connection_time": manager.max_connection_time,
            "max_messages_per_connection": manager.max_messages_per_connection,
            "cleanup_interval": manager.cleanup_interval
        }
        
        return stats
    
    except Exception as e:
        logger.error(f"Error getting WebSocket stats: {e}")
        return {"error": "Failed to get WebSocket statistics"}

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
        
        # Debug: Log what we received from frontend
        logger.info(f"Raw feedback data received: {feedback.model_dump()}")
        logger.info(f"Sentiment field from Pydantic model: {feedback.sentiment}")
        
        # Format feedback data for telemetry using the correct field names
        feedback_data = {
            # Original fields
            "relevance": feedback.relevance,
            "factual_accuracy": feedback.factual_accuracy,
            "source_quality": feedback.source_quality,
            "clarity": feedback.clarity,
            "question_rating": feedback.question_rating,
            "user_category": feedback.user_category,
            "tags": feedback.tags,
            "feedback_text": feedback.feedback_text,
            "model_answer": feedback.model_answer,
            "timestamp": feedback.timestamp or datetime.datetime.now().isoformat(),
            "source": "http_fallback",
            
            # New inline feedback fields
            "feedback_type": feedback.feedback_type,
            "sentiment": feedback.sentiment,
            "analysis_quality": feedback.analysis_quality,
            "difficulty": feedback.difficulty,
            "faults": feedback.faults,
            
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