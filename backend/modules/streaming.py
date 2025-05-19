"""
Streaming utilities for ATLAS.

This module provides functions for creating and streaming Server-Sent Events (SSE)
to clients, with built-in telemetry instrumentation.
"""

import json
import logging
import time
import asyncio
from typing import Dict, Any, Generator, Optional, List, Callable, AsyncGenerator
from datetime import datetime

# Import telemetry modules at the beginning to avoid UnboundLocalError
from backend.telemetry.core import create_span, SpanKind
from backend.telemetry.constants import SpanAttributes, SpanNames, OpenInferenceSpanKind
from backend.telemetry import BaseSpanManager
from backend.telemetry.spans import register_span
from backend.retrievers.hansard_retriever import format_document_for_citation

logger = logging.getLogger(__name__)

def format_sse_message(data: Dict[str, Any], event: Optional[str] = None) -> str:
    """
    Format a Server-Sent Event (SSE) message.
    
    Args:
        data: The data to send, will be JSON-encoded
        event: Optional event type
        
    Returns:
        Formatted SSE message string
    """
    message = f"data: {json.dumps(data)}\n"
    if event:
        message = f"event: {event}\n{message}"
    return f"{message}\n"

def create_error_message(error_type: str, detail: str) -> Dict[str, Any]:
    """
    Create a standardized error message.
    
    Args:
        error_type: The type of error
        detail: Error details or message
        
    Returns:
        Dictionary with error information
    """
    return {
        "error": {
            "type": error_type,
            "detail": detail,
            "timestamp": time.time()
        }
    }

def create_complete_message(
    text: str, 
    citations: Optional[List[Dict[str, Any]]] = None,
    references: Optional[Dict[str, Any]] = None,
    qa_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Create a message for a completed response.
    
    Args:
        text: The complete text response
        citations: Optional list of citations
        references: Optional references data
        qa_id: Optional QA ID
        
    Returns:
        Dictionary with completion data
    """
    return {
        "qaId": qa_id,
        "responseComplete": True,
        "responseText": text,
        "citations": citations or [],
        "references": references or {},
        "timestamp": time.time()
    }

def create_chunk_message(
    chunk: str, 
    qa_id: Optional[str] = None,
    chunk_type: str = "text"
) -> Dict[str, Any]:
    """
    Create a message for a response chunk.
    
    Args:
        chunk: The text chunk
        qa_id: Optional QA ID
        chunk_type: Type of chunk (text, citation, etc.)
        
    Returns:
        Dictionary with chunk data
    """
    return {
        "qaId": qa_id,
        "responseComplete": False,
        "chunk": {
            "type": chunk_type,
            "text": chunk
        },
        "timestamp": time.time()
    }

async def stream_response_chunks(
    chunks_generator: Generator[str, None, None],
    qa_id: str,
    session_id: Optional[str] = None,
    span: Optional[Any] = None,
    chunk_processor: Optional[Callable[[str], str]] = None,
    create_streaming_span: bool = True
) -> AsyncGenerator[str, None]:
    """
    Stream response chunks as server-sent events (SSE).
    
    This function formats text chunks from an LLM into SSE messages
    and tracks various metrics during streaming.
    
    Args:
        chunks_generator: Generator that yields response chunks
        qa_id: QA ID for the response
        session_id: Optional session ID for telemetry
        span: Optional parent span
        chunk_processor: Optional function to process each chunk before sending
        create_streaming_span: Whether to create a streaming span (set to False to prevent redundant spans)
        
    Yields:
        Formatted SSE messages
    """
    # Skip creating a redundant streaming span if requested
    if not create_streaming_span:
        # Just stream chunks without telemetry
        chunk_count = 0
        try:
            for chunk in chunks_generator:
                # Process chunk if processor provided
                if chunk_processor:
                    chunk = chunk_processor(chunk)
                
                # Create chunk message
                message = create_chunk_message(chunk, qa_id)
                
                # Yield formatted SSE message
                yield format_sse_message(message)
                
        except Exception as e:
            # Log the error
            logger.error(f"Error streaming response: {e}", exc_info=True)
            
            # Yield error message
            error_message = create_error_message("streaming_error", str(e))
            yield format_sse_message(error_message, event="error")
            
            # Re-raise to allow higher-level error handling
            raise
        
        return
        
    # Otherwise, create a streaming span as normal
    with create_span(
        SpanNames.STREAMING_RESPONSE,
        attributes={
            # Session identifiers
            SpanAttributes.SESSION_ID: session_id,
            SpanAttributes.QA_ID: qa_id,
            
            # Span categorization
            "openinference.span.kind": OpenInferenceSpanKind.PROCESSOR,
        },
        session_id=session_id,  # Critical for session association
        kind=SpanKind.INTERNAL,
        link_to_current=True
    ) as streaming_span:
        chunk_count = 0
        total_chars = 0
        start_time = time.time()
        
        try:
            for chunk in chunks_generator:
                # Process chunk if processor provided
                if chunk_processor:
                    chunk = chunk_processor(chunk)
                
                # Update counts
                chunk_count += 1
                total_chars += len(chunk)
                
                # Create chunk message
                message = create_chunk_message(chunk, qa_id)
                
                # Record telemetry with basic counts
                streaming_span.set_attribute("chunk_count", chunk_count)
                streaming_span.set_attribute("total_chars", total_chars)
                
                # Yield formatted SSE message
                yield format_sse_message(message)
            
            # Calculate processing time
            processing_time = time.time() - start_time
            
            # Create a summary of the streaming process
            summary = f"Streamed {chunk_count} chunks ({total_chars} characters)"
            
            # Create detailed information
            details = {
                "chunk_count": chunk_count,
                "total_characters": total_chars,
                "avg_chars_per_chunk": total_chars / max(1, chunk_count),
                "processing_time_seconds": processing_time,
                "streaming_complete": True
            }
            
            # Set standard outputs using BaseSpanManager
            BaseSpanManager.set_standard_outputs(
                span=streaming_span,
                summary=summary,
                details=details,
                span_kind=OpenInferenceSpanKind.PROCESSOR
            )
            
        except Exception as e:
            # Calculate processing time up to error
            processing_time = time.time() - start_time
            
            # Set error using BaseSpanManager
            error_summary = f"Error streaming response: {str(e)}"
            BaseSpanManager.set_standard_outputs(
                span=streaming_span,
                summary=error_summary,
                error=e,
                details={
                    "chunk_count": chunk_count,
                    "total_characters": total_chars,
                    "processing_time_seconds": processing_time,
                    "streaming_complete": False,
                    "error_during_streaming": True
                },
                span_kind=OpenInferenceSpanKind.PROCESSOR
            )
            
            # Log the error
            logger.error(f"Error streaming response: {e}", exc_info=True)
            
            # Yield error message
            error_message = create_error_message("streaming_error", str(e))
            yield format_sse_message(error_message, event="error")
            
            # Re-raise to allow higher-level error handling
            raise

def stream_documents_as_references(
    documents: List[Any],
    qa_id: str,
    session_id: Optional[str] = None,
    citation_limit: int = 10,
    span: Optional[Any] = None
) -> str:
    """
    Format retrieved documents as references in a single SSE message.
    
    This function transforms document objects into citation/reference data
    suitable for display in the frontend and formats them as an SSE message.
    
    Args:
        documents: List of retrieved documents
        qa_id: QA ID for the response
        session_id: Optional session ID for telemetry
        citation_limit: Maximum number of citations to include (displayed by default)
        span: Optional parent span
        
    Returns:
        Formatted SSE message with references
    """
    # Create a span for the citation and reference generation
    with create_span(
        SpanNames.DOCUMENT_REFERENCES,
        attributes={
            SpanAttributes.SESSION_ID: session_id,
            SpanAttributes.QA_ID: qa_id,
            "document_count": len(documents),
            "citation_limit": citation_limit,
            "openinference.span.kind": OpenInferenceSpanKind.REFERENCES,
        },
        session_id=session_id
    ) as ref_span:
        # Register span for feedback association
        register_span(session_id, f"{qa_id}_references", ref_span.get_span_context().span_id)
        
        try:
            # Format documents as citations
            citations = []
            for idx, doc in enumerate(documents[:citation_limit]):
                # Format the document as a citation
                citation = format_document_for_citation(doc, idx)
                citation["idx"] = idx
                citations.append(citation)
            
            # Get all citations for telemetry
            all_citations = []
            for doc in documents:
                cite = format_document_for_citation(doc)
                if cite:
                    all_citations.append(cite)
            
            # Create references object for frontend display
            references = {
                "qa_id": qa_id,
                "citations": citations
            }
            
            # Set reference information on span for telemetry
            ref_span.set_attribute("description", "Citations and references for the RAG response")
            ref_span.set_attribute("citations", json.dumps(citations))
            ref_span.set_attribute("all_citations", json.dumps(all_citations))
            ref_span.set_attribute("references", json.dumps(references))
            ref_span.set_attribute("citation_count", len(citations))
            
            # Create the SSE response
            ref_message = {
                "type": "references",
                "qa_id": qa_id,
                "citations": citations,
                "allCitations": all_citations
            }
            
            # Format as SSE
            return format_sse_message(ref_message, event="references")
            
        except Exception as e:
            # Set error using BaseSpanManager
            error_summary = f"Error formatting references: {str(e)}"
            BaseSpanManager.set_standard_outputs(
                span=ref_span,
                summary=error_summary,
                error=e,
                span_kind=OpenInferenceSpanKind.REFERENCES
            )
            
            # Log the error
            logger.error(f"Error formatting references: {e}", exc_info=True)
            
            # Return error message
            error_message = create_error_message("reference_error", str(e))
            return format_sse_message(error_message, event="error") 