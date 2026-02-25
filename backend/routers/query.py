"""
Query API endpoints for ATLAS.

Includes streaming Q&A and async query processing endpoints.
"""

import os
import json
import asyncio
import logging
import uuid
from fastapi import APIRouter, HTTPException, Request, Body
from fastapi.responses import StreamingResponse

from backend.modules.config import (
    get_retriever,
    get_corpus_options,
    get_citation_limit,
    get_search_k
)
from backend.modules.document_retrieval import retrieve_documents_with_telemetry
from backend.modules.streaming import (
    format_sse_message,
    create_error_message,
    create_complete_message,
    stream_response_chunks,
    stream_documents_as_references
)
from backend.modules.response import generate_response_with_telemetry
from backend.modules.sensitive_contexts import detect_sensitive_contexts
from backend.telemetry import (
    SpanAttributes,
    SpanNames,
    OpenInferenceSpanKind,
    Status,
    StatusCode,
    create_rag_pipeline_span
)
from backend.telemetry.config_attrs import get_test_target_attributes
from backend.services.llm_resource_manager import llm_resource_manager

logger = logging.getLogger(__name__)

router = APIRouter()

# Check async queue availability
environment = os.getenv("ENVIRONMENT", "development").lower()
async_queue_available = False

if environment in ["production", "staging"]:
    try:
        from backend.services.queue_manager import get_queue_manager
        async_queue_available = True
    except ImportError:
        pass
else:
    try:
        from backend.services.queue_manager import get_queue_manager
        async_queue_available = True
    except ImportError:
        pass


def _get_valid_corpus_values():
    """Get list of valid corpus filter values dynamically."""
    corpus_options = get_corpus_options()
    return [opt.get("value") for opt in corpus_options if opt.get("value")]


@router.post("/api/ask/stream")
async def ask_stream(data: dict = Body(...)):
    """
    Stream an answer to a question using retrieved documents and a language model.
    """
    # Extract request data with input sanitization
    question = data.get("question", "").strip()

    # Get filters from new dynamic format
    filters = data.get("filters", {})
    previous_filters = data.get("previous_filters", {})

    # Get faceted filters (from FacetedSearch component, v1.5+ corpora)
    facet_filters = data.get("facet_filters", {})

    # Extract corpus filter for backward compatibility with existing retrieval logic
    corpus_filter = filters.get("corpus_filtering", "all")

    # Input validation and sanitization
    if not question or len(question) > 2000:
        raise HTTPException(status_code=400, detail="Question is required and must be under 2000 characters")

    # Basic injection prevention
    dangerous_patterns = ["ignore previous", "system:", "<script", "javascript:"]
    if any(pattern in question.lower() for pattern in dangerous_patterns):
        raise HTTPException(status_code=400, detail="Invalid question content")

    # Validate corpus filter dynamically
    valid_corpus_values = _get_valid_corpus_values()
    if corpus_filter not in valid_corpus_values:
        corpus_filter = "all"

    chat_history = data.get("chat_history", [])
    session_id = data.get("session_id", str(uuid.uuid4()))
    qa_id = data.get("qa_id", str(uuid.uuid4()))
    provider = data.get("provider", None)  # Optional LLM provider override

    # Define async generator for streaming response
    async def response_generator():
        # Use nonlocal to access/modify the qa_id from the outer scope
        nonlocal qa_id

        # Get test target configuration for telemetry
        test_target_attrs = get_test_target_attributes()

        # Create base attributes for the span
        pipeline_attributes = {
            SpanAttributes.SESSION_ID: session_id,
            SpanAttributes.QA_ID: qa_id,
            "user_query": question,
            "is_streaming": True,
            "corpus_filter": corpus_filter,
            "filters": filters,
            "has_facet_filters": bool(facet_filters),
            "llm_provider": provider,
            "openinference.span.kind": OpenInferenceSpanKind.AGENT,
        }

        # Add all test target attributes individually with flat names
        for key, value in test_target_attrs.items():
            flat_key = key.replace(".", "_")
            pipeline_attributes[flat_key] = value

        # Remove keys that would clash with explicit parameters
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
                    parent_span=parent_span
                )

                await asyncio.sleep(0.001)

                if sensitive_contexts:
                    logger.warning(f"Detected sensitive contexts for session {session_id}: {sensitive_contexts}")

                # Check if retriever is available
                retriever = get_retriever()
                if retriever is None:
                    error_msg = "No corpus configured. Please use the corpus wizard to set up a corpus first."
                    logger.error(error_msg)
                    yield f"data: {json.dumps({'error': error_msg})}\n\n"
                    return

                # Step 1: HNSW retrieval with per-corpus balanced reranking
                final_k = get_search_k()

                documents, qa_id = retrieve_documents_with_telemetry(
                    query=question,
                    retriever=retriever,
                    session_id=session_id,
                    qa_id=qa_id,
                    corpus_filter=corpus_filter,
                    k=final_k,
                    facet_filters=facet_filters if facet_filters else None
                )

                # Optionally augment with manifest summary
                try:
                    from backend.modules.manifest_context import (
                        looks_like_manifest_question,
                        get_manifest_document,
                    )
                    if looks_like_manifest_question(question):
                        manifest_doc = get_manifest_document()
                        if manifest_doc is not None:
                            documents = [manifest_doc] + list(documents)
                            parent_span.set_attribute("manifest_context_included", True)
                except Exception:
                    pass

                # If no documents were retrieved, return an error
                if not documents:
                    error_msg = create_error_message(
                        "retrieval_error",
                        "No relevant documents found for your query."
                    )
                    yield format_sse_message(error_msg, event="error")
                    return

                logger.info(f"Retrieved {len(documents)} balanced documents (per-corpus reranked)")

                # Debug: Show sample content from first few reranked docs
                for i, doc in enumerate(documents[:3]):
                    content_preview = doc.page_content[:200] if hasattr(doc, 'page_content') else str(doc)[:200]
                    metadata = getattr(doc, 'metadata', {})
                    corpus = metadata.get('corpus', 'unknown')
                    logger.info(f"Reranked doc {i+1} ({corpus}): {content_preview}...")

                parent_span.set_attribute(SpanAttributes.DOCUMENT_COUNT, len(documents))

                # Acquire LLM resource slot before generation
                await llm_resource_manager.acquire_llm_slot()

                try:
                    # Generate and stream the response
                    response_gen, qa_id = generate_response_with_telemetry(
                        question=question,
                        documents=documents,
                        session_id=session_id,
                        qa_id=qa_id,
                        chat_history=chat_history,
                        corpus_filter=corpus_filter,
                        provider=provider
                    )

                    # Stream response chunks
                    full_response = ""
                    chunk_count = 0

                    async for sse_message in stream_response_chunks(
                        chunks_generator=response_gen,
                        qa_id=qa_id,
                        session_id=session_id,
                        create_streaming_span=False
                    ):
                        if not sse_message.endswith('\n\n'):
                            sse_message += '\n\n'
                        yield sse_message
                        await asyncio.sleep(0)

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

                    # Set top-level span info
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
                    logger.error(f"Error in streaming response: {e}")
                    parent_span.record_exception(e)
                    parent_span.set_status(Status(StatusCode.ERROR, "Streaming response error"))

                    error_msg = create_error_message(
                        "streaming_error",
                        "An error occurred while processing your request"
                    )
                    yield format_sse_message(error_msg, event="error")

                finally:
                    llm_resource_manager.release_llm_slot()

            except Exception as e:
                logger.error(f"Error in RAG pipeline: {e}")
                parent_span.record_exception(e)
                parent_span.set_status(Status(StatusCode.ERROR, "RAG pipeline error"))

                llm_resource_manager.release_llm_slot()

                error_msg = create_error_message(
                    "pipeline_error",
                    "An error occurred while processing your request"
                )
                yield format_sse_message(error_msg, event="error")

    response = StreamingResponse(response_generator(), media_type="text/event-stream")
    response.headers["Content-Type"] = "text/event-stream"
    response.headers["Cache-Control"] = "no-cache"
    response.headers["Connection"] = "keep-alive"
    response.headers["X-Accel-Buffering"] = "no"
    return response


@router.post("/api/ask/async")
async def ask_async(data: dict = Body(...), request: Request = None):
    """
    Submit an LLM query for async processing.
    Returns immediately with a request ID for status checking.
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
            try:
                user_id = getattr(request.state, 'user_id', None)
            except:
                pass

        # Get queue manager
        from backend.services.queue_manager import get_queue_manager
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


@router.get("/api/ask/async/{request_id}")
async def get_async_status(request_id: str):
    """
    Get the status and result of an async LLM request.
    """
    if not async_queue_available:
        raise HTTPException(
            status_code=503,
            detail="Async processing not available. Redis queue not configured."
        )

    try:
        from backend.services.queue_manager import get_queue_manager
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
