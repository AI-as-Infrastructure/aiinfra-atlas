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

from backend.telemetry import create_span, SpanAttributes, SpanNames, OpenInferenceSpanKind
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
    span: Optional[Any] = None
) -> List[Document]:
    """
    Retrieve documents using the provided retriever.
    
    Args:
        query: Query string
        retriever: Document retriever
        k: Number of documents to retrieve
        corpus_filter: Optional corpus filter
        search_type: Type of search to perform
        span: Optional parent span
        
    Returns:
        List of retrieved documents
    """
    with create_span(
        SpanNames.CONTEXT_RETRIEVAL,
        attributes={
            "query": query,
            "k": k,
            "corpus_filter": corpus_filter or "all",
            "search_type": search_type,
            "openinference.span.kind": OpenInferenceSpanKind.RETRIEVER
        },
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
            # Perform retrieval
            if needs_large_retrieval:
                logger.debug(f"Performing large retrieval (k={large_k}) for corpus filtering")
                retrieval_span.set_attribute("actual_k", large_k)
                documents = retriever.get_relevant_documents(query, k=large_k)
            else:
                logger.debug(f"Performing standard retrieval (k={k})")
                retrieval_span.set_attribute("actual_k", k)
                documents = retriever.get_relevant_documents(query, k=k)
            
            # Record document count
            retrieval_span.set_attribute(SpanAttributes.DOCUMENT_COUNT, len(documents))
            
            # Get document distribution for telemetry
            distribution = get_document_distribution(documents)
            for field, values in distribution.items():
                if len(values) <= 20:  # Avoid setting extremely large attributes
                    retrieval_span.set_attribute(f"distribution.{field}", ",".join(values))
                retrieval_span.set_attribute(f"distribution.{field}.count", len(values))
            
            # Add document distribution as JSON
            retrieval_span.set_attribute("distribution_json", json.dumps(distribution))
            
            # Include preview of first few documents for debugging
            doc_previews = []
            for i, doc in enumerate(documents[:3]):  # First 3 docs only
                if hasattr(doc, 'page_content') and hasattr(doc, 'metadata'):
                    content_preview = doc.page_content[:100] + "..." if len(doc.page_content) > 100 else doc.page_content
                    doc_previews.append({
                        "index": i,
                        "content_preview": content_preview,
                        "metadata": {k: v for k, v in doc.metadata.items() 
                                 if k in ["date", "title", "source", "corpus", "page"]}
                    })
            
            # Store document previews as JSON
            if doc_previews:
                retrieval_span.set_attribute("document_previews_json", json.dumps(doc_previews))
            
            # Apply corpus filter if needed
            if corpus_filter and corpus_filter.lower() != "all":
                logger.debug(f"Applying corpus filter: {corpus_filter}")
                documents = apply_corpus_filter(documents, corpus_filter, retrieval_span)
                
                # Limit to requested k after filtering
                if len(documents) > k:
                    logger.debug(f"Limiting filtered documents to {k}")
                    documents = documents[:k]
                    retrieval_span.set_attribute("limited_after_filtering", True)
                else:
                    retrieval_span.set_attribute("limited_after_filtering", False)
                
                # Record final document count
                retrieval_span.set_attribute("filtered_document_count", len(documents))
            
            return documents
            
        except Exception as e:
            # Record error in telemetry
            retrieval_span.record_exception(e)
            retrieval_span.set_attribute("retrieval_error", str(e))
            
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
    Retrieve documents with full telemetry instrumentation.
    
    This function creates its own telemetry span and is suitable for use
    in high-level code that doesn't create spans itself.
    
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
    
    with create_span(
        SpanNames.CONTEXT_RETRIEVAL,
        attributes={
            SpanAttributes.SESSION_ID: session_id,
            SpanAttributes.QA_ID: qa_id,
            "query": query,
            "k": k or get_search_k(),
            "corpus_filter": corpus_filter or "all",
            "openinference": {
                "span": {
                    "kind": OpenInferenceSpanKind.RETRIEVER
                }
            }
        }
    ) as qa_span:
        try:
            # Retrieve documents
            documents = retrieve_documents(
                query=query,
                retriever=retriever,
                k=k,
                corpus_filter=corpus_filter
            )
            
            # Record success
            qa_span.set_attribute("retrieval_success", True)
            qa_span.set_attribute(SpanAttributes.DOCUMENT_COUNT, len(documents))
            
            # Get distribution of document metadata for telemetry
            document_distribution = get_document_distribution(documents)
            qa_span.set_attribute("distribution", document_distribution)
            
            # Add timestamps for timing analysis
            qa_span.set_attribute("retrieval_timestamp", datetime.now().isoformat())
            
            return documents, qa_id
            
        except Exception as e:
            # Record error in telemetry
            qa_span.record_exception(e)
            qa_span.set_attribute("retrieval_success", False)
            
            # Log the error
            logger.error(f"Error in document retrieval with telemetry: {e}", exc_info=True)
            
            # Re-raise to allow higher-level error handling
            raise 