"""
Streaming utilities for ATLAS.

This module provides functions for creating and streaming Server-Sent Events (SSE)
to clients, with built-in telemetry instrumentation.
"""

import json
import logging
import time
from typing import Dict, Any, Generator, Optional, List, Callable, AsyncGenerator

# Import telemetry modules at the beginning to avoid UnboundLocalError
from backend.telemetry.core import create_span, SpanKind
from backend.telemetry.constants import SpanAttributes, SpanNames, OpenInferenceSpanKind

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
            SpanAttributes.SESSION_ID: session_id,
            SpanAttributes.QA_ID: qa_id,
            
            # Critical: Set the kind in the exact format Phoenix expects
            "type": "PROCESSOR",
            "span_kind": "PROCESSOR",
            "otel.kind": "PROCESSOR",
            "openinference.span.kind": "PROCESSOR",
            
            "processor.type": "stream_formatter",
            "component.type": "sse",
            "processor.description": "Formats and streams text chunks as server-sent events"
        },
        kind=SpanKind.INTERNAL,
        link_to_current=True
    ) as streaming_span:
        chunk_count = 0
        total_chars = 0
        
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
                
                # Record telemetry
                streaming_span.set_attribute("chunk_count", chunk_count)
                streaming_span.set_attribute("total_chars", total_chars)
                
                # Yield formatted SSE message
                yield format_sse_message(message)
                
            # Record final metrics
            streaming_span.set_attribute("final_chunk_count", chunk_count)
            streaming_span.set_attribute("final_char_count", total_chars)
            streaming_span.set_attribute("streaming_complete", True)
            
        except Exception as e:
            # Record error in telemetry
            streaming_span.record_exception(e)
            streaming_span.set_attribute("streaming_error", str(e))
            streaming_span.set_attribute("streaming_complete", False)
            
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
    with create_span(
        SpanNames.DOCUMENT_REFERENCES,
        attributes={
            # Session identifiers
            SpanAttributes.SESSION_ID: session_id,
            SpanAttributes.QA_ID: qa_id,
            
            # Document information
            SpanAttributes.DOCUMENT_COUNT: len(documents),
            "citation_limit": citation_limit,
            
            # Detailed document information
            "description": f"Formatting {len(documents)} documents as references/citations for display",
            "operation": "citation_formatting",
            "citation_display_limit": citation_limit,
            "processing_type": "document_references",
            
            # Critical: Set the kind in the exact format Phoenix expects
            # Use a single, proven span kind format that Phoenix definitely understands
            "type": OpenInferenceSpanKind.REFERENCES,
            "span_kind": OpenInferenceSpanKind.REFERENCES,
            
            # Standard OpenTelemetry span kind
            "otel.kind": "PROCESSOR",  # Standard OTel kind
            
            # Use the most direct attribute Phoenix specifically looks for
            "openinference.span.kind": OpenInferenceSpanKind.REFERENCES,
            
            "processor.type": "citation_formatter",
            "processor.description": "Transforms document objects into structured citations and references for display"
        },
        kind=SpanKind.INTERNAL,  # Use INTERNAL kind for processors
        link_to_current=True
    ) as ref_span:
        # Preserve all documents for full analysis view
        all_documents = documents.copy()
        
        # Create a limited set for default display
        limited_documents = documents
        if citation_limit > 0 and len(documents) > citation_limit:
            limited_documents = documents[:citation_limit]
            ref_span.set_attribute("documents_limited", True)
        else:
            ref_span.set_attribute("documents_limited", False)
        
        ref_span.set_attribute("final_document_count", len(limited_documents))
        ref_span.set_attribute("total_document_count", len(all_documents))
        
        # Format documents as references
        references = {}
        citations = []
        all_citations = []
        
        try:
            for i, doc in enumerate(documents):
                if hasattr(doc, 'metadata'):
                    # Generate citation ID
                    citation_id = f"citation-{i+1}"
                    
                    # Extract metadata
                    metadata = doc.metadata.copy() if hasattr(doc, 'metadata') else {}
                    
                    # Extract text content
                    text = doc.page_content if hasattr(doc, 'page_content') else str(doc)
                    
                    # Add to references
                    references[citation_id] = {
                        "text": text,
                        "metadata": metadata
                    }
                    
                    # Add to citations list
                    url = metadata.get('url', '')
                    
                    citations.append({
                        "id": citation_id,
                        "text": text[:100] + "..." if len(text) > 100 else text,
                        "content": text,  # Include full content
                        "full_content": text,  # Include full content in alternative field
                        "url": url,  # Include URL directly
                        "metadata": {
                            k: v for k, v in metadata.items() 
                            if k in ["date", "title", "source", "corpus", "page", "url"]
                        }
                    })
            
            # Process all documents into citations
            for i, doc in enumerate(all_documents):
                if i >= len(citations) and hasattr(doc, 'metadata'):
                    # Only process documents that weren't already processed
                    # Generate citation ID
                    citation_id = f"citation-{i+1}"
                    
                    # Extract metadata
                    metadata = doc.metadata.copy() if hasattr(doc, 'metadata') else {}
                    
                    # Extract text content
                    text = doc.page_content if hasattr(doc, 'page_content') else str(doc)
                    
                    # Add to all_citations list
                    url = metadata.get('url', '')
                    
                    all_citations.append({
                        "id": citation_id,
                        "text": text[:100] + "..." if len(text) > 100 else text,
                        "content": text,  # Include full content
                        "full_content": text,  # Include full content in alternative field
                        "url": url,  # Include URL directly
                        "metadata": {
                            k: v for k, v in metadata.items() 
                            if k in ["date", "title", "source", "corpus", "page", "url"]
                        }
                    })
            
            # Create message with references
            message = {
                "qaId": qa_id,
                "responseComplete": False,
                "references": references,
                "citations": citations,
                "allCitations": all_citations,  # Send all citations for the modal view
                "timestamp": time.time()
            }
            
            ref_span.set_attribute("citation_count", len(citations))
            ref_span.set_attribute("all_citation_count", len(all_citations))
            ref_span.set_attribute("reference_count", len(references))
            
            # Add citations to telemetry for analysis
            # Store select important fields as individual attributes
            for i, citation in enumerate(citations):
                if i < 15:  # Limit to 15 citations to avoid too many attributes
                    ref_span.set_attribute(f"citation.{i}.id", citation.get("id", ""))
                    ref_span.set_attribute(f"citation.{i}.text", citation.get("text", "")[:200])
                    
                    # Include key metadata
                    for key in ["date", "title", "source", "corpus"]:
                        if key in citation.get("metadata", {}):
                            ref_span.set_attribute(f"citation.{i}.{key}", str(citation["metadata"][key]))

            # Store full citation data as JSON for Phoenix UI
            ref_span.set_attribute("citations_json", json.dumps(citations))  
            ref_span.set_attribute("all_citations_json", json.dumps(all_citations))
            
            # Add a summary for Info display in Phoenix
            summary_data = []
            for i, citation in enumerate(citations[:5]):  # First 5 citations only
                title = citation.get("metadata", {}).get("title", f"Document {i+1}")
                source = citation.get("metadata", {}).get("source", "Unknown")
                date = citation.get("metadata", {}).get("date", "")
                summary_data.append(f"{i+1}. {title} ({source}, {date})")
            
            if summary_data:
                ref_span.set_attribute("citations_summary", "\n".join(summary_data))
            
            # Also attach a shortened version of each document to the parent span
            # for telemetry analysis and debugging (limited to keep span size reasonable)
            doc_samples = []
            for i, doc in enumerate(documents[:5]):  # Limit to first 5 docs
                if hasattr(doc, 'page_content') and hasattr(doc, 'metadata'):
                    content = doc.page_content[:300] + "..." if len(doc.page_content) > 300 else doc.page_content
                    meta = {k: v for k, v in doc.metadata.items() if k in ["date", "title", "source", "corpus", "page"]}
                    doc_samples.append({"content": content, "metadata": meta})
            
            ref_span.set_attribute("document_samples_json", json.dumps(doc_samples))
            
            # Set output for Phoenix display
            citations_summary = f"Generated {len(citations)} citations from {len(documents)} documents"
            
            # Create nicely formatted citation summary with details
            if summary_data:
                formatted_summary = "\n".join(summary_data)
                citation_output = f"{citations_summary}\n\n{formatted_summary}"
            else:
                citation_output = citations_summary
            
            # Set all output attributes directly on the main span
            # Primary content field - most important for Phoenix display
            ref_span.set_attribute("content", citation_output)
            
            # Set using the output method if available
            if hasattr(ref_span, "set_output"):
                ref_span.set_output(citation_output)
            
            # Also set standard output attributes for maximum compatibility
            ref_span.set_attribute("output", citation_output)
            ref_span.set_attribute("output.value", citation_output)
            ref_span.set_attribute(SpanAttributes.OUTPUT, citation_output)
            
            return format_sse_message(message, event="references")
            
        except Exception as e:
            # Record error in telemetry
            ref_span.record_exception(e)
            ref_span.set_attribute("reference_error", str(e))
            
            # Log the error
            logger.error(f"Error formatting references: {e}", exc_info=True)
            
            # Return error message
            error_message = create_error_message("reference_error", str(e))
            return format_sse_message(error_message, event="error") 