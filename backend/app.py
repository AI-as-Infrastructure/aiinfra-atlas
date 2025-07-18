import os

from fastapi import FastAPI, HTTPException, Request, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
import os
from dotenv import load_dotenv
import asyncio
import json
import datetime
import logging
import time
import gc
import weakref
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
from backend.services.validation_service import validation_service, SessionData
from pydantic import BaseModel
from typing import Dict, List, Optional, Any
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

# Add telemetry middleware to set user preference for each request
@app.middleware("http")
async def telemetry_middleware(request: Request, call_next):
    """Middleware to set user telemetry preference based on request headers."""
    from backend.telemetry import set_user_telemetry_preference
    
    # Set user telemetry preference based on headers
    user_enabled = set_user_telemetry_preference(request)
    
    # Log for debugging
    if request.url.path.startswith("/api/"):
        logger.info(f"Telemetry middleware: User telemetry {'enabled' if user_enabled else 'disabled'} for {request.url.path}")
    
    response = await call_next(request)
    return response

@app.middleware("http")
async def security_middleware(request: Request, call_next):
    """Basic security middleware for research prototype"""
    # Request size limit
    max_size = 10 * 1024 * 1024  # 10MB limit
    content_length = request.headers.get("content-length")
    if content_length and int(content_length) > max_size:
        return JSONResponse(
            status_code=413,
            content={"error": "Request too large", "max_size": f"{max_size // (1024*1024)}MB"}
        )
    
    # Rate limiting based on environment configuration
    rate_limit = int(os.getenv("RATE_LIMIT_PER_MINUTE", "240"))
    client_ip = request.client.host if request.client else "unknown"
    
    if not hasattr(app.state, "rate_limit_store"):
        app.state.rate_limit_store = {}
    
    current_time = time.time()
    window_start = current_time - 60  # 1 minute window
    
    # Clean old entries and check rate
    if client_ip not in app.state.rate_limit_store:
        app.state.rate_limit_store[client_ip] = []
    
    app.state.rate_limit_store[client_ip] = [
        t for t in app.state.rate_limit_store[client_ip] if t > window_start
    ]
    
    if len(app.state.rate_limit_store[client_ip]) >= rate_limit:
        return JSONResponse(
            status_code=429,
            content={"error": "Rate limit exceeded. Please wait before making more requests."}
        )
    
    app.state.rate_limit_store[client_ip].append(current_time)
    response = await call_next(request)
    return response

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

# WebSocket functionality removed for security and simplicity
# All real-time functionality now uses HTTP endpoints

# LLM Resource Management
class LLMResourceManager:
    def __init__(self):
        # Limit concurrent LLM requests to prevent memory exhaustion
        self.max_concurrent_requests = int(os.getenv("LLM_MAX_CONCURRENT", "10"))
        self.request_semaphore = asyncio.Semaphore(self.max_concurrent_requests)
        
        # Track active LLM instances for memory cleanup
        self.active_llm_instances = weakref.WeakSet()
        self.last_cleanup = time.time()
        self.cleanup_interval = 300  # 5 minutes
        
        # Response size limits
        self.max_response_tokens = int(os.getenv("LLM_MAX_RESPONSE_TOKENS", "4000"))
        self.max_response_chars = int(os.getenv("LLM_MAX_RESPONSE_CHARS", "32000"))
        
        logger.info(f"LLM Resource Manager initialized: max_concurrent={self.max_concurrent_requests}")
    
    async def acquire_llm_slot(self):
        """Acquire a slot for LLM processing"""
        await self.request_semaphore.acquire()
        
        # Periodic cleanup
        if time.time() - self.last_cleanup > self.cleanup_interval:
            self.cleanup_memory()
    
    def release_llm_slot(self):
        """Release a slot for LLM processing"""
        self.request_semaphore.release()
    
    def cleanup_memory(self):
        """Perform memory cleanup"""
        try:
            # Clean up LLM instances
            self._cleanup_llm_instances()
            
            # Clean up vector store connections
            self._cleanup_vector_stores()
            
            # Force garbage collection
            gc.collect()
            
            # Log active instances
            active_count = len(self.active_llm_instances)
            logger.info(f"LLM memory cleanup: {active_count} active instances")
            
            self.last_cleanup = time.time()
            
        except Exception as e:
            logger.error(f"Error during LLM memory cleanup: {e}")
    
    def _cleanup_llm_instances(self):
        """Clean up LLM instances that are no longer needed"""
        try:
            # Get list of current instances (weak references may be None)
            current_instances = [inst for inst in self.active_llm_instances if inst is not None]
            
            # Explicit cleanup for instances that support it
            for instance in current_instances:
                try:
                    # Check if instance has cleanup methods
                    if hasattr(instance, 'cleanup'):
                        instance.cleanup()
                    elif hasattr(instance, 'close'):
                        instance.close()
                    elif hasattr(instance, '__del__'):
                        # Let Python handle cleanup
                        pass
                except Exception as inst_error:
                    logger.debug(f"Error cleaning up LLM instance: {inst_error}")
            
            logger.debug(f"Cleaned up {len(current_instances)} LLM instances")
            
        except Exception as e:
            logger.error(f"Error during LLM instance cleanup: {e}")
    
    def _cleanup_vector_stores(self):
        """Clean up vector store connections"""
        try:
            from backend.modules.vector_store_manager import get_vector_store_manager
            vector_manager = get_vector_store_manager()
            
            # Clean up expired connections
            vector_manager._cleanup_expired_connections()
            
            logger.debug("Cleaned up vector store connections")
            
        except Exception as e:
            logger.debug(f"Error cleaning up vector stores: {e}")
    
    def register_llm_instance(self, llm_instance):
        """Register an LLM instance for tracking"""
        self.active_llm_instances.add(llm_instance)
        
        # Register cleanup callback if possible
        if hasattr(llm_instance, 'register_cleanup_callback'):
            llm_instance.register_cleanup_callback(self._instance_cleanup_callback)
    
    def _instance_cleanup_callback(self, instance):
        """Callback when an LLM instance is cleaned up"""
        logger.debug(f"LLM instance cleaned up: {type(instance).__name__}")
    
    def dispose_llm_instance(self, llm_instance):
        """Explicitly dispose of an LLM instance"""
        try:
            if hasattr(llm_instance, 'cleanup'):
                llm_instance.cleanup()
            elif hasattr(llm_instance, 'close'):
                llm_instance.close()
            
            # Remove from tracking
            self.active_llm_instances.discard(llm_instance)
            
            logger.debug(f"Disposed LLM instance: {type(llm_instance).__name__}")
            
        except Exception as e:
            logger.error(f"Error disposing LLM instance: {e}")
    
    def check_response_size(self, response_text: str) -> bool:
        """Check if response exceeds size limits"""
        if len(response_text) > self.max_response_chars:
            logger.warning(f"Response truncated: {len(response_text)} chars > {self.max_response_chars} limit")
            return False
        return True
    
    def truncate_response(self, response_text: str) -> str:
        """Truncate response to size limits"""
        if len(response_text) > self.max_response_chars:
            truncated = response_text[:self.max_response_chars]
            # Try to truncate at last complete sentence
            last_period = truncated.rfind('.')
            if last_period > self.max_response_chars * 0.8:  # If we can find a period in the last 20%
                truncated = truncated[:last_period + 1]
            return truncated + "\n\n[Response truncated due to length limits]"
        return response_text

llm_resource_manager = LLMResourceManager()

# WebSocket endpoint removed - use HTTP /api/feedback endpoint instead

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
    try:
        data = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON in request body")
    
    query = data.get("query", "").strip()
    session_id = data.get("session_id")
    qa_id = data.get("qa_id")
    corpus_filter = data.get("corpus_filter", "all")
    
    if not query or len(query) > 2000:
        raise HTTPException(status_code=400, detail="Query is required and must be under 2000 characters")

    # Basic injection prevention
    dangerous_patterns = ["ignore previous", "system:", "<script", "javascript:"]
    if any(pattern in query.lower() for pattern in dangerous_patterns):
        raise HTTPException(status_code=400, detail="Invalid query content")

    if corpus_filter not in ["all", "1901_au", "1901_nz", "1901_uk"]:
        corpus_filter = "all"
    
    # Use our document retrieval utility with retry logic for transient failures
    max_retries = 2
    retry_delay = 1  # Start with 1 second delay
    
    for attempt in range(max_retries + 1):
        try:
            documents, qa_id = retrieve_documents_with_telemetry(
                query=query,
                retriever=get_retriever(),
                session_id=session_id,
                qa_id=qa_id,
                corpus_filter=corpus_filter
            )
            break  # Success, exit retry loop
        except TimeoutError:
            if attempt < max_retries:
                import time
                time.sleep(retry_delay)
                retry_delay *= 2  # Exponential backoff
                continue
            raise HTTPException(status_code=503, detail="Document retrieval timed out")
        except ConnectionError:
            if attempt < max_retries:
                import time
                time.sleep(retry_delay)
                retry_delay *= 2  # Exponential backoff
                continue
            raise HTTPException(status_code=503, detail="Unable to connect to document store")
        except ValueError:
            # Don't retry validation errors
            raise HTTPException(status_code=400, detail="Invalid query parameters")
        except Exception:
            if attempt < max_retries:
                import time
                time.sleep(retry_delay)
                retry_delay *= 2  # Exponential backoff
                continue
            raise HTTPException(status_code=503, detail="Document retrieval temporarily unavailable")
    
    # Format documents as citations for frontend display with graceful error handling
    citations = []
    for idx, doc in enumerate(documents):
        try:
            # Import the format_document_for_citation function
            from backend.retrievers.hansard_retriever import format_document_for_citation
            citation = format_document_for_citation(doc, idx)
            if citation:
                citations.append(citation)
        except Exception:
            # Continue processing other documents if one citation fails
            continue
    
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
    # Extract request data with input sanitization
    question = data.get("question", "").strip()
    corpus_filter = data.get("corpus_filter", "all")
    previous_corpus_filter = data.get("previous_corpus_filter", "all")
    
    # Input validation and sanitization
    if not question or len(question) > 2000:
        raise HTTPException(status_code=400, detail="Question is required and must be under 2000 characters")

    # Basic injection prevention
    dangerous_patterns = ["ignore previous", "system:", "<script", "javascript:"]
    if any(pattern in question.lower() for pattern in dangerous_patterns):
        raise HTTPException(status_code=400, detail="Invalid question content")

    if corpus_filter not in ["all", "1901_au", "1901_nz", "1901_uk"]:
        corpus_filter = "all"
    if previous_corpus_filter not in ["all", "1901_au", "1901_nz", "1901_uk"]:
        previous_corpus_filter = "all"
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
                
                # Acquire LLM resource slot before generation
                await llm_resource_manager.acquire_llm_slot()
                
                try:
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
                    logger.error(f"Error in streaming response: {e}")
                    # Record error in parent span
                    parent_span.record_exception(e)
                    # Use generic error message for telemetry to avoid exposing sensitive info
                    parent_span.set_status(Status(StatusCode.ERROR, "Streaming response error"))
                    
                    # Create a sanitized error message for the client
                    # Do not expose internal exception details to client
                    error_msg = create_error_message(
                        "streaming_error",
                        "An error occurred while processing your request"
                    )
                    yield format_sse_message(error_msg, event="error")
                    
                finally:
                    # Always release the LLM resource slot
                    llm_resource_manager.release_llm_slot()
                    
            except Exception as e:
                # Handle any outer exceptions
                logger.error(f"Error in RAG pipeline: {e}")
                parent_span.record_exception(e)
                # Use generic error message for telemetry to avoid exposing sensitive info
                parent_span.set_status(Status(StatusCode.ERROR, "RAG pipeline error"))
                
                # Release LLM resource slot on error
                llm_resource_manager.release_llm_slot()
                
                # Create error message for client
                error_msg = create_error_message(
                    "pipeline_error",
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

@app.get("/api/cache/stats")
async def get_cache_stats(request: Request):
    """Return prompt cache statistics for monitoring."""
    # Check if authentication is required based on environment
    auth_required = os.getenv("VITE_USE_COGNITO_AUTH", "false").lower() == "true"
    
    if auth_required:
        # Get the authorization header
        auth_header = request.headers.get("Authorization")
        if not auth_header:
            raise HTTPException(
                status_code=401,
                detail="Authorization header required"
            )
        
        # Extract the token from the header
        try:
            token = auth_header.split(" ")[1] if " " in auth_header else auth_header
        except (IndexError, AttributeError):
            raise HTTPException(
                status_code=401,
                detail="Invalid authorization header format"
            )
        
        # Verify the token (will raise HTTPException if invalid)
        user = await verify_cognito_token(token)
        
        # Check if the user is authenticated
        if not user.get("authenticated", False):
            raise HTTPException(
                status_code=403,
                detail="Unauthorized access to cache statistics"
            )
    
    try:
        from backend.modules.prompt_cache import get_cache_statistics
        cache_stats = get_cache_statistics()
        
        return {
            "cache_statistics": cache_stats,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting cache statistics: {e}")
        return {
            "error": "Failed to retrieve cache statistics",
            "cache_statistics": {},
            "timestamp": datetime.now().isoformat()
        }

@app.post("/api/cache/clear")
async def clear_cache(request: Request):
    """Clear the prompt cache."""
    # Check if authentication is required based on environment
    auth_required = os.getenv("VITE_USE_COGNITO_AUTH", "false").lower() == "true"
    
    if auth_required:
        # Get the authorization header
        auth_header = request.headers.get("Authorization")
        if not auth_header:
            raise HTTPException(
                status_code=401,
                detail="Authorization header required"
            )
        
        # Extract the token from the header
        try:
            token = auth_header.split(" ")[1] if " " in auth_header else auth_header
        except (IndexError, AttributeError):
            raise HTTPException(
                status_code=401,
                detail="Invalid authorization header format"
            )
        
        # Verify the token (will raise HTTPException if invalid)
        user = await verify_cognito_token(token)
        
        # Check if the user is authenticated
        if not user.get("authenticated", False):
            raise HTTPException(
                status_code=403,
                detail="Unauthorized access to cache management"
            )
    
    try:
        from backend.modules.prompt_cache import clear_prompt_cache
        clear_prompt_cache()
        
        logger.info("Prompt cache cleared via API")
        
        return {
            "message": "Prompt cache cleared successfully",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error clearing cache: {e}")
        return {
            "error": "Failed to clear cache",
            "timestamp": datetime.now().isoformat()
        }

# WebSocket stats endpoint removed - WebSocket functionality no longer available

# --- HTTP Feedback endpoint ---
@app.post("/api/feedback", response_model=FeedbackResponse)
async def submit_feedback(feedback: UserFeedback, request: Request):
    """
    Submit user feedback via HTTP.
    Primary feedback submission endpoint (WebSocket removed for security).
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
        logger.info(f"AI validation field from Pydantic model: {feedback.ai_validation}")
        logger.info(f"AI agreement field from Pydantic model: {feedback.ai_agreement}")
        
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
            "additional_comments": feedback.additional_comments,  # Missing field added
            "faults": feedback.faults,
            
            # Include rich context data from frontend
            "test_target": feedback.test_target,
            "question": feedback.question,
            "answer": feedback.answer,
            "citations": feedback.citations,
            "citation_count": len(feedback.citations) if feedback.citations else 0,
            
            # AI-Enhanced feedback fields (minimal addition)
            "ai_validation": feedback.ai_validation,
            "ai_agreement": feedback.ai_agreement,
            "ratings": feedback.ratings,
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
                logger.error(f"Error processing HTTP feedback: {e}")
                return FeedbackResponse(
                    message="Error processing feedback",
                    status="error"
                )
    except Exception as e:
        logger.error(f"Error in HTTP feedback endpoint: {e}")
        return FeedbackResponse(
            message="An error occurred processing your feedback",
            status="error"
        )

# --- Validation Models ---
class ValidationRequest(BaseModel):
    session_id: str
    qa_id: str
    question: str
    answer: str
    citations: List[Dict[str, Any]]
    metadata: Dict[str, Any]
    validation_mode: Optional[str] = None  # "default" or "alternate"

class ValidationResponse(BaseModel):
    success: bool
    message: str
    validation_result: Optional[Dict[str, Any]] = None
    markdown_export: Optional[str] = None
    validation_config: Optional[Dict[str, Any]] = None

# --- Session Validation endpoint ---
@app.post("/api/validate_session", response_model=ValidationResponse)
async def validate_session(validation_request: ValidationRequest, request: Request):
    """
    Validate a RAG session using an alternate LLM to provide structured feedback.
    
    This endpoint:
    1. Exports the session data to structured Markdown
    2. Sends it to a validation LLM (configured via .env)
    3. Returns structured feedback to guide human reviewers
    """
    
    # Check if validation is enabled
    if not validation_service.is_enabled():
        return ValidationResponse(
            success=False,
            message="Session validation is disabled",
            validation_config=validation_service.get_validation_config_info()
        )
    
    try:
        # Create session data object
        session_data = SessionData(
            session_id=validation_request.session_id,
            qa_id=validation_request.qa_id,
            question=validation_request.question,
            answer=validation_request.answer,
            citations=validation_request.citations,
            metadata=validation_request.metadata,
            timestamp=datetime.datetime.now().isoformat()
        )
        
        # Export session to Markdown
        markdown_export = validation_service.export_session_to_markdown(session_data)
        
        # Validate the session
        validation_result = validation_service.validate_session(
            session_data, 
            validation_mode=validation_request.validation_mode
        )
        
        # Convert validation result to dict for response
        result_dict = {
            "session_id": validation_result.session_id,
            "qa_id": validation_result.qa_id,
            "validation_model": validation_result.validation_model,
            "validation_provider": validation_result.validation_provider,
            "validation_mode": validation_result.validation_mode,
            "feedback": validation_result.feedback,
            "structured_feedback": validation_result.structured_feedback,
            "validation_timestamp": validation_result.validation_timestamp,
            "processing_time": validation_result.processing_time
        }
        
        logger.info(f"Session validation completed for {validation_request.session_id} using {validation_result.validation_provider}/{validation_result.validation_model}")
        
        return ValidationResponse(
            success=True,
            message="Session validation completed successfully",
            validation_result=result_dict,
            markdown_export=markdown_export,
            validation_config=validation_service.get_validation_config_info()
        )
        
    except Exception as e:
        logger.error(f"Error during session validation: {e}")
        return ValidationResponse(
            success=False,
            message="Error during session validation",
            validation_config=validation_service.get_validation_config_info()
        )

# --- Validation Configuration endpoint ---
@app.get("/api/validate_config")
async def get_validation_config():
    """
    Get current validation configuration information.
    """
    return validation_service.get_validation_config_info()

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

# WebSocket async status endpoint removed - use HTTP polling on /api/ask/async/{request_id} instead

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