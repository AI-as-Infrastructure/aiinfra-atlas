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

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables from config/.env (relative to project root)
project_root = os.path.dirname(os.path.dirname(__file__))
env_path = os.path.join(project_root, "config", ".env")
if os.path.exists(env_path):
    logger.info(f"Loading environment variables from: {env_path}")
    load_dotenv(env_path)
else:
    logger.error(f"Environment file not found at: {env_path}")

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
from backend.telemetry.config_attrs import get_test_target_attributes

if not telemetry_initialized:
    raise RuntimeError("Telemetry is not initialized. The app cannot start without telemetry.")

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
                            success = log_user_feedback(session_id, qa_id, feedback)
                            
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
        "citation_limit": retriever_config.get("citation_limit"),
        "large_retrieval_size": retriever_config.get("large_retrieval_size"),
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
def ask(data: dict = Body(...)):
    """Handle a Q&A turn with telemetry."""
    question = data.get('question')
    chat_history = data.get('chat_history', [])
    session_id = data.get('session_id')
    qa_id = data.get('qa_id')
    corpus_filter = data.get("corpus_filter", "all")
    feedback = data.get('feedback')
    provider = data.get('provider')  # Allow client to specify the provider

    if not question:
        return JSONResponse(content={"error": "No 'question' provided."}, status_code=400)

    # Retrieve documents
    documents, qa_id = retrieve_documents_with_telemetry(
        query=question,
        retriever=get_retriever(),
        session_id=session_id,
        qa_id=qa_id,
        corpus_filter=corpus_filter
    )
    
    # Apply corpus filter
    documents = filter_documents_with_telemetry(
        documents=documents,
        corpus_filter=corpus_filter,
        session_id=session_id,
        qa_id=qa_id
    )
    
    # Generate response
    response_generator, qa_id = generate_response_with_telemetry(
        question=question,
        documents=documents,
        session_id=session_id,
        qa_id=qa_id,
        chat_history=chat_history,
        corpus_filter=corpus_filter,
        provider=provider  # Pass the provider if specified
    )
    
    # Collect the entire response
    response_text = ""
    for chunk in response_generator:
        response_text += chunk
    
    # Log user feedback if provided
    if feedback:
        log_user_feedback(session_id, qa_id, feedback)

    return {
        "result": response_text, 
        "session_id": session_id, 
        "qa_id": qa_id,
        "document_count": len(documents)
    }

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
        from backend.telemetry import create_span
        
        # Get test target configuration for telemetry
        test_target_attrs = get_test_target_attributes()
        
        with create_span(
            SpanNames.RAG_PIPELINE,
            attributes={
                SpanAttributes.SESSION_ID: session_id,
                SpanAttributes.QA_ID: qa_id,
                SpanAttributes.INPUT_VALUE: question,
                "is_streaming": True,
                "corpus_filter": corpus_filter,
                "previous_corpus_filter": previous_corpus_filter,
                "llm_provider": provider,  # Add provider to telemetry
                # Use flat structure for OpenInference attributes
                "openinference.span.kind": OpenInferenceSpanKind.AGENT,
                # Include all test target attributes
                **test_target_attrs  # Spread the test target attributes
            },
            session_id=session_id
        ) as parent_span:
            try:
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
                    session_id=session_id
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
                
                # Parse the references to get citations for the parent span
                try:
                    refs_data = json.loads(references_message.split("data: ")[1])
                    all_citations = refs_data.get("allCitations", [])
                    
                    # Store citations as JSON string in parent span
                    parent_span.set_attribute("citations_json", json.dumps(all_citations))
                    
                    # Store select citation fields as individual attributes for better visibility
                    for i, citation in enumerate(all_citations[:10]):  # Limit to 10 citations
                        parent_span.set_attribute(f"citation.{i}.id", citation.get("id", ""))
                        parent_span.set_attribute(f"citation.{i}.text", citation.get("text", "")[:200])
                        
                        # Include key metadata 
                        for key in ["date", "title", "source", "corpus"]:
                            if key in citation.get("metadata", {}):
                                parent_span.set_attribute(f"citation.{i}.{key}", str(citation["metadata"][key]))
                    
                    # Add a short document summary for Phoenix UI
                    if all_citations:
                        doc_summary = []
                        for i, citation in enumerate(all_citations[:5]):
                            first_100_chars = citation.get("content", "")[:100] + "..."
                            doc_summary.append(f"Doc {i+1}: {first_100_chars}")
                        
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
                logger.error(f"Error in streaming response: {e}", exc_info=True)
                # Record error in parent span
                parent_span.record_exception(e)
                parent_span.set_status(Status(StatusCode.ERROR, str(e)))
                
                # Send error message to client
                error_msg = create_error_message("streaming_error", str(e))
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
def diagnostics():
    """Return diagnostic information to help debug issues."""
    import os
    
    # Check critical environment variables
    env_vars = {
        "TEST_TARGET": os.getenv("TEST_TARGET"),
        "REDIS_HOST": os.getenv("REDIS_HOST"),
        "REDIS_PORT": os.getenv("REDIS_PORT"),
        "REDIS_PASSWORD": os.getenv("REDIS_PASSWORD", "***REDACTED***") is not None,
        "PHOENIX_API_KEY": os.getenv("PHOENIX_API_KEY", "***REDACTED***") is not None,
        "ANTHROPIC_API_KEY": os.getenv("ANTHROPIC_API_KEY", "***REDACTED***") is not None,
        "OPENAI_API_KEY": os.getenv("OPENAI_API_KEY", "***REDACTED***") is not None,
    }
    
    # Get basic config info
    config_info = {}
    try:
        config = get_config()
        retriever_config = config.get("retriever_config", {})
        # Add Chroma and corpus selector config values from environment
        config["CHROMA_COLLECTION_NAME"] = os.getenv("CHROMA_COLLECTION_NAME")
        config["MULTI_CORPUS_VECTORSTORE"] = os.getenv("MULTI_CORPUS_VECTORSTORE")
        config_info = {
            "target_id": retriever_config.get("target_id"),
            "llm_provider": config.get("llm_provider"),
            "llm_model": config.get("llm_model"),
            "embedding_model": retriever_config.get("embedding_model"),
            "citation_limit": retriever_config.get("citation_limit"),
            "large_retrieval_size": retriever_config.get("large_retrieval_size"),
        }
    except Exception as e:
        config_info = {"error": str(e)}
    
    # Return all diagnostics
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
        
        # Format feedback data for telemetry
        feedback_data = {
            "answer_rating": feedback.answer_rating,
            "citations_rating": feedback.citations_rating,
            "feedback_text": feedback.feedback_text,
            "timestamp": datetime.datetime.now().isoformat(),
            "source": "http_fallback"
        }
        
        # Use the session context to ensure spans are properly associated
        with using_session(session_id):
            try:
                # Log user feedback
                success = log_user_feedback(session_id, qa_id, feedback_data)
                
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
                    message=f"Error processing feedback: {str(e)}",
                    status="error"
                )
    except Exception as e:
        logger.error(f"Error in HTTP feedback endpoint: {e}", exc_info=True)
        return FeedbackResponse(
            message="An error occurred processing your feedback",
            status="error"
        )

# --- Entrypoint for running with Uvicorn ---
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.app:app", host="0.0.0.0", port=8000, reload=True)