"""
Document retrieval utilities for ATLAS.

This module provides functions for retrieving and processing documents,
with built-in telemetry instrumentation.
"""

import logging
import uuid
import json
from typing import List, Dict, Any, Optional, Union, Tuple
from datetime import datetime

from langchain_core.documents.base import Document
from langchain_core.embeddings import Embeddings
from langchain_core.vectorstores import VectorStore

from backend.telemetry import create_span, SpanAttributes, SpanNames, OpenInferenceSpanKind, SpanKind, BaseSpanManager, get_span_manager, RAGSpanManager
from backend.modules.corpus_filtering import apply_corpus_filter, filter_documents_with_telemetry
from backend.modules.config import get_search_k, get_citation_limit, get_large_retrieval_size

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
    # Determine retriever type and implementation details
    retriever_type = getattr(retriever, "type", search_type)
    retriever_name = type(retriever).__name__
    chroma_search = "Chroma" in retriever_name or hasattr(retriever, "vectorstore") and "Chroma" in type(retriever.vectorstore).__name__
    is_hnsw = True  # Chroma uses HNSW by default
    
    # Skip creating a redundant span if requested
    if not create_parent_span:
        # Default K value if not provided
        if k is None:
            k = get_search_k()
        
        # Use large retrieval size for corpus filtering
        large_k = get_large_retrieval_size()
        
        # Determine if we should perform a larger search for corpus filtering
        needs_large_retrieval = (
            corpus_filter and
            corpus_filter.lower() != "all" and
            hasattr(retriever, "supports_corpus_filtering") and
            retriever.supports_corpus_filtering
        )
        
        try:
            # Perform retrieval
            if needs_large_retrieval:
                logger.debug(f"Performing large retrieval (k={large_k}) for corpus filtering")
                documents = retriever.get_relevant_documents(query, k=large_k)
            else:
                logger.debug(f"Performing standard retrieval (k={k})")
                documents = retriever.get_relevant_documents(query, k=k)
            
            # Apply corpus filter if needed
            if corpus_filter and corpus_filter.lower() != "all":
                logger.debug(f"Applying corpus filter: {corpus_filter}")
                documents = apply_corpus_filter(
                    documents, 
                    corpus_filter
                )
                
                # Limit to requested k after filtering
                if len(documents) > k:
                    logger.debug(f"Limiting filtered documents to {k}")
                    documents = documents[:k]
            
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
        kind=SpanKind.INTERNAL,
        link_to_current=True
    ) as retrieval_span:
        # Use default search_k if not provided
        if k is None:
            k = get_search_k()
            retrieval_span.set_attribute("k_from_config", True)
        else:
            retrieval_span.set_attribute("k_from_config", False)
        
        # Use large retrieval size for corpus filtering
        large_k = get_large_retrieval_size()
        
        # Determine if we should perform a larger search for corpus filtering
        needs_large_retrieval = (
            corpus_filter and
            corpus_filter.lower() != "all" and
            hasattr(retriever, "supports_corpus_filtering") and
            retriever.supports_corpus_filtering
        )
        
        retrieval_span.set_attribute("needs_large_retrieval", needs_large_retrieval)
        
        try:
            start_time = None
            # Record start time for performance tracking
            start_time = datetime.now()
            
            # Perform retrieval
            if needs_large_retrieval:
                logger.debug(f"Performing large retrieval (k={large_k}) for corpus filtering")
                retrieval_span.set_attribute("actual_k", large_k)
                retrieval_span.set_attribute("retrieval_mode", "large_corpus_search")
                documents = retriever.get_relevant_documents(query, k=large_k)
            else:
                logger.debug(f"Performing standard retrieval (k={k})")
                retrieval_span.set_attribute("actual_k", k)
                retrieval_span.set_attribute("retrieval_mode", "standard_search")
                documents = retriever.get_relevant_documents(query, k=k)
            
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
            
            # Set standard outputs using BaseSpanManager
            if corpus_filter and corpus_filter.lower() != "all":
                summary = f"Retrieved {len(documents)} documents for query with corpus filter: {corpus_filter}"
            else:
                summary = f"Retrieved {len(documents)} documents for query"
                
            # Create detailed information
            details = {
                "retriever_type": retriever_type,
                "retriever_name": retriever_name,
                "is_chroma": chroma_search,
                "search_algorithm": "hnsw" if is_hnsw else "unknown",
                "k_requested": k,
                "corpus_filter": corpus_filter or "all",
                "retrieval_mode": "large_corpus_search" if needs_large_retrieval else "standard_search",
                "document_count": len(documents)
            }
            
            # Add processing time if available
            if processing_time:
                details["processing_time_seconds"] = processing_time
                
            # Add distribution information
            for field, values in distribution.items():
                details[f"distribution_{field}_count"] = len(values)
                if len(values) <= 10:  # Keep manageable size for display
                    details[f"distribution_{field}"] = values
            
            # Set standard outputs with BaseSpanManager
            BaseSpanManager.set_standard_outputs(
                span=retrieval_span,
                summary=summary,
                details=details,
                span_kind=OpenInferenceSpanKind.RETRIEVER
            )
            
            # Add document previews using BaseSpanManager
            if documents:
                BaseSpanManager.add_document_preview(retrieval_span, documents[:3])
            
            # Apply corpus filter if needed
            if corpus_filter and corpus_filter.lower() != "all":
                logger.debug(f"Applying corpus filter: {corpus_filter}")
                documents = apply_corpus_filter(
                    documents, 
                    corpus_filter
                )
                
                # Limit to requested k after filtering
                if len(documents) > k:
                    logger.debug(f"Limiting filtered documents to {k}")
                    documents = documents[:k]
                    retrieval_span.set_attribute("limited_after_filtering", True)
                else:
                    retrieval_span.set_attribute("limited_after_filtering", False)
                
                # Update document count and output
                retrieval_span.set_attribute("filtered_document_count", len(documents))
                
                # Update the outputs with filtered information
                filter_summary = f"Retrieved {len(documents)} documents after filtering"
                filter_details = details.copy()
                filter_details["filtered_document_count"] = len(documents)
                
                # Update outputs with filtered information
                BaseSpanManager.set_standard_outputs(
                    span=retrieval_span,
                    summary=filter_summary,
                    details=filter_details,
                    span_kind=OpenInferenceSpanKind.RETRIEVER
                )
            
            return documents
            
        except Exception as e:
            # Handle error with BaseSpanManager
            error_summary = f"Error retrieving documents: {str(e)}"
            BaseSpanManager.set_standard_outputs(
                span=retrieval_span,
                summary=error_summary,
                error=e,
                span_kind=OpenInferenceSpanKind.RETRIEVER
            )
            
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
    
    This function directly calls retrieve_documents with the necessary parameters
    and links the retrieval span to the parent RAG pipeline span.
    
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
    
    try:
        # Get information about the retriever implementation
        retriever_name = type(retriever).__name__
        vectorstore_type = "unknown"
        index_type = "unknown"
        
        # Try to extract vectorstore type
        if hasattr(retriever, "vectorstore"):
            vectorstore_type = type(retriever.vectorstore).__name__
            
        # Check if it's Chroma (most common case)
        if "Chroma" in retriever_name or "Chroma" in vectorstore_type:
            index_type = "chroma_hnsw"
            
        # Log retriever info
        logger.info(f"Using retriever: {retriever_name} with vectorstore: {vectorstore_type} and index type: {index_type}")
        
        # Create telemetry span with proper attributes - DON'T USE SPAN MANAGER HERE
        with create_span(
            SpanNames.CONTEXT_RETRIEVAL,
            attributes={
                # Core identification attributes
                SpanAttributes.SESSION_ID: session_id,
                SpanAttributes.QA_ID: qa_id,
                
                # Input information
                SpanAttributes.INPUT_VALUE: query,
                "corpus_filter": corpus_filter or "all",
                
                # Span categorization
                "openinference.span.kind": OpenInferenceSpanKind.RETRIEVER,
                "openinference.retriever.type": retriever_name
            },
            session_id=session_id
        ) as span:
            # Add this line to explicitly register the span
            from backend.telemetry.spans import register_span
            register_span(session_id, qa_id, span.get_span_context().span_id)
            
            # Call retrieve_documents with create_parent_span=False to avoid creating a duplicate span
            documents = retrieve_documents(
                query=query,
                retriever=retriever,
                k=k,
                corpus_filter=corpus_filter,
                search_type="similarity",
                session_id=session_id,
                qa_id=qa_id,
                create_parent_span=False  # Critical: Don't create another span
            )
            
            # Update span with results
            span.set_attribute("document_count", len(documents))
            
            # Use BaseSpanManager for standard outputs
            summary = f"Retrieved {len(documents)} documents for query"
            details = {
                "retriever_name": retriever_name,
                "document_count": len(documents),
                "corpus_filter": corpus_filter or "all"
            }
            
            BaseSpanManager.set_standard_outputs(
                span=span,
                summary=summary,
                details=details,
                span_kind=OpenInferenceSpanKind.RETRIEVER
            )
            
            # Add document previews 
            BaseSpanManager.add_document_preview(span, documents[:3])
            
            return documents, qa_id
        
    except Exception as e:
        # Log the error
        logger.error(f"Error in document retrieval with telemetry: {e}", exc_info=True)
        
        # Re-raise to allow higher-level error handling
        raise 