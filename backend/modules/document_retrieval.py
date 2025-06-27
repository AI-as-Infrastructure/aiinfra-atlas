"""
Document retrieval utilities for ATLAS.

This module provides functions for retrieving and processing documents,
with built-in telemetry instrumentation.
"""

import logging
import uuid
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime

from langchain_core.documents.base import Document

from backend.telemetry import create_span, SpanAttributes, SpanNames, OpenInferenceSpanKind
from opentelemetry.trace import SpanKind, Status, StatusCode
from backend.modules.config import get_search_k

logger = logging.getLogger(__name__)

def extract_metadata_fields(
    documents: List[Document],
    fields: List[str] = ["date", "title", "source", "corpus", "page"]
) -> List[Dict[str, Any]]:
    """
    Extract specified metadata fields from documents.
    
    Args:
        documents: List of documents
        fields: List of metadata fields to extract
        
    Returns:
        List of dictionaries with extracted metadata
    """
    result = []
    for doc in documents:
        if hasattr(doc, 'metadata'):
            metadata = {
                field: doc.metadata.get(field, None)
                for field in fields
                if field in doc.metadata
            }
            result.append(metadata)
    return result

def get_document_distribution(documents: List[Document]) -> Dict[str, List[str]]:
    """
    Get distribution of documents by various metadata fields.
    
    Args:
        documents: List of documents
        
    Returns:
        Dictionary with metadata fields as keys and lists of unique values as values
    """
    distribution = {
        "corpus": set(),
        "date": set(),
        "source": set(),
        "title": set()
    }
    
    for doc in documents:
        if hasattr(doc, 'metadata'):
            for field in distribution:
                if field in doc.metadata and doc.metadata[field]:
                    distribution[field].add(str(doc.metadata[field]))
    
    # Convert sets to sorted lists for better readability
    return {k: sorted(list(v)) for k, v in distribution.items()}

def retrieve_documents(
    query: str,
    retriever: Any,
    k: Optional[int] = None,
    corpus_filter: Optional[str] = None,
    search_type: str = "similarity",
    session_id: Optional[str] = None,
    qa_id: Optional[str] = None,
    create_parent_span: bool = True
) -> List[Document]:
    """
    Retrieve documents using the provided retriever.
    
    Args:
        query: Query string
        retriever: Document retriever
        k: Number of documents to retrieve
        corpus_filter: Optional corpus filter
        search_type: Type of search to perform
        session_id: Session ID for telemetry linkage
        qa_id: Question/answer ID for telemetry linkage
        create_parent_span: Whether to create the parent context retrieval span
                           (set to False to prevent redundant spans)
        
    Returns:
        List of retrieved documents
    """
    # Determine retriever type and implementation details for telemetry
    retriever_type = getattr(retriever, "type", search_type)
    retriever_name = type(retriever).__name__
    chroma_search = "Chroma" in retriever_name or hasattr(retriever, "vectorstore") and "Chroma" in type(retriever.vectorstore).__name__
    
    # Skip creating a redundant span if requested
    if not create_parent_span:
        # Default K value if not provided
        if k is None:
            k = get_search_k()
        
        try:
            # Corpus-agnostic document retrieval - let the retriever handle all corpus logic
            logger.info(f"🔍 Document retrieval: corpus_filter='{corpus_filter}', k={k}")
            
            # Debug: Check what retriever we're actually using
            logger.info(f"🔧 Retriever type: {type(retriever)}")
            logger.info(f"🔧 Retriever class: {retriever.__class__.__name__}")
            logger.info(f"🔧 Has _handle_corpus_retrieval: {hasattr(retriever, '_handle_corpus_retrieval')}")
            
            # Simple call to retriever - it handles all corpus-specific logic internally
            config = {"corpus_filter": corpus_filter} if corpus_filter else None
            logger.info(f"🔧 Calling retriever.invoke with config={config}, k={k}")
            documents = retriever.invoke(query, config=config, k=k)
            logger.info(f"🔧 Retriever.invoke returned {len(documents)} documents")
            
            logger.info(f"📄 Retrieved {len(documents)} documents from retriever")
            return documents
            
        except Exception as e:
            # Log the error
            logger.error(f"Error retrieving documents: {e}", exc_info=True)
            
            # Re-raise to allow higher-level error handling
            raise
    
    with create_span(
        SpanNames.CONTEXT_RETRIEVAL,
        attributes={
            # Session identifiers
            SpanAttributes.SESSION_ID: session_id,
            SpanAttributes.QA_ID: qa_id,
            
            # Input information
            SpanAttributes.INPUT_VALUE: query,
            SpanAttributes.DOCUMENT_COUNT: 0,  # Will be updated after retrieval
            "corpus_filter": corpus_filter or "all",
            
            # Span categorization
            "openinference.span.kind": OpenInferenceSpanKind.RETRIEVER,
            "openinference.retriever.type": retriever_type,
        },
        session_id=session_id,  # Critical for session association
        kind=OpenInferenceSpanKind.RETRIEVER,  # Pass the OpenInference kind here
        otel_kind=SpanKind.INTERNAL  # Pass the OpenTelemetry kind as otel_kind
    ) as retrieval_span:
        # Use default search_k if not provided
        if k is None:
            k = get_search_k()
            retrieval_span.set_attribute("k_from_config", True)
        else:
            retrieval_span.set_attribute("k_from_config", False)
        
        # Set attributes for corpus filtering at HNSW level
        retrieval_span.set_attribute("corpus_filtering_at_hnsw", corpus_filter and corpus_filter.lower() != "all")
        
        try:
            start_time = None
            # Record start time for performance tracking
            start_time = datetime.now()
            
            # Corpus-agnostic document retrieval - let the retriever handle all corpus logic
            logger.info(f"🔍 TELEMETRY: Document retrieval: corpus_filter='{corpus_filter}', k={k}")
            
            # Debug: Check what retriever we're actually using
            logger.info(f"🔧 Retriever type: {type(retriever)}")
            logger.info(f"🔧 Retriever class: {retriever.__class__.__name__}")
            logger.info(f"🔧 Has _handle_corpus_retrieval: {hasattr(retriever, '_handle_corpus_retrieval')}")
            
            # Set basic telemetry attributes
            retrieval_span.set_attribute("actual_k", k)
            retrieval_span.set_attribute("corpus_filter", corpus_filter or "all")
            retrieval_span.set_attribute("retrieval_mode", "delegated_to_retriever")
            
            # Simple call to retriever - it handles all corpus-specific logic internally
            config = {"corpus_filter": corpus_filter} if corpus_filter else None
            logger.info(f"🔧 Calling retriever.invoke with config={config}, k={k}")
            documents = retriever.invoke(query, config=config, k=k)
            logger.info(f"🔧 Retriever.invoke returned {len(documents)} documents")
            
            logger.debug(f"Retrieved {len(documents)} documents from retriever")
            
            # Calculate processing time if start_time was recorded
            processing_time = None
            if start_time:
                end_time = datetime.now()
                processing_time = (end_time - start_time).total_seconds()
                retrieval_span.set_attribute("processing_time_seconds", processing_time)
            
            # Update document count attribute
            retrieval_span.set_attribute(SpanAttributes.DOCUMENT_COUNT, len(documents))
            
            # Get document distribution for detailed information
            distribution = get_document_distribution(documents)
            
            # Create corpus-agnostic summary
            summary = f"Retrieved {len(documents)} documents from retriever"
            if corpus_filter and corpus_filter.lower() != "all":
                summary += f" (corpus: {corpus_filter})"
                
            # Create basic telemetry details (corpus-agnostic)
            details = {
                "retriever_type": retriever_type,
                "retriever_name": retriever_name,
                "k_requested": k,
                "corpus_filter": corpus_filter or "all",
                "document_count": len(documents),
                "has_corpus_filter": bool(corpus_filter and corpus_filter.lower() != "all")
            }
            
            # Add processing time if available
            if processing_time:
                details["processing_time_seconds"] = processing_time
                
            # Add distribution information
            for field, values in distribution.items():
                details[f"distribution_{field}_count"] = len(values)
                if len(values) <= 10:  # Keep manageable size for display
                    details[f"distribution_{field}"] = values
            
            # Set span attributes for Phoenix UI display (only once, with final information)
            retrieval_span.set_attribute("summary", summary)
            retrieval_span.set_attribute("output", summary)
            retrieval_span.set_attribute("output.value", summary[:500])
            retrieval_span.set_attribute("openinference.span.kind", OpenInferenceSpanKind.RETRIEVER)
            for key, value in details.items():
                retrieval_span.set_attribute(key, value)
            
            # Add document previews
            if documents:
                for i, doc in enumerate(documents[:3]):
                    retrieval_span.set_attribute(f"document_{i}_preview", doc.page_content[:200])
            
            return documents
            
        except Exception as e:
            # Handle error with direct span attributes
            error_summary = f"Error retrieving documents: {str(e)}"
            retrieval_span.set_attribute("summary", error_summary)
            retrieval_span.set_attribute("output", error_summary)
            retrieval_span.set_attribute("output.value", error_summary[:500])
            retrieval_span.set_attribute("openinference.span.kind", OpenInferenceSpanKind.RETRIEVER)
            retrieval_span.set_status(Status(StatusCode.ERROR, str(e)))
            
            # Log the error
            logger.error(f"Error retrieving documents: {e}", exc_info=True)
            
            # Re-raise to allow higher-level error handling
            raise

def retrieve_documents_with_telemetry(
    query: str,
    retriever: Any,
    session_id: Optional[str] = None,
    qa_id: Optional[str] = None,
    corpus_filter: Optional[str] = None,
    k: Optional[int] = None
) -> Tuple[List[Document], str]:
    """
    Retrieve documents with telemetry instrumentation.
    
    This is a simple wrapper around retrieve_documents that ensures QA ID generation
    and returns the expected tuple format.
    
    Args:
        query: Query string
        retriever: Document retriever
        session_id: Session ID for telemetry
        qa_id: QA ID for telemetry
        corpus_filter: Optional corpus filter
        k: Number of documents to retrieve
        
    Returns:
        Tuple of (list of documents, QA ID)
    """
    # Generate QA ID if not provided
    if not qa_id:
        qa_id = str(uuid.uuid4())
    
    # Call the main retrieve_documents function (which creates telemetry spans)
    documents = retrieve_documents(
        query=query,
        retriever=retriever,
        k=k,
        corpus_filter=corpus_filter,
        search_type="similarity",
        session_id=session_id,
        qa_id=qa_id,
        create_parent_span=True  # Create proper telemetry spans
    )
    
    return documents, qa_id 