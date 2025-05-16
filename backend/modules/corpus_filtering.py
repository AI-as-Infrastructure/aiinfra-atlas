"""
Corpus filtering utilities for ATLAS.

This module provides utilities for filtering documents by corpus and analyzing
corpus distributions. All functions are instrumented with telemetry spans.
"""

import logging
from typing import Dict, List, Any, Optional
from collections import Counter
from langchain_core.documents.base import Document

from backend.telemetry import create_span, SpanAttributes, SpanNames, OpenInferenceSpanKind

logger = logging.getLogger(__name__)

def get_corpus_distribution(documents: List[Document]) -> Dict[str, int]:
    """
    Get distribution of documents by corpus.
    
    Args:
        documents: List of documents
        
    Returns:
        Dictionary with corpus as key and count as value
    """
    with create_span(
        "get_corpus_distribution",
        attributes={
            "document_count": len(documents)
        }
    ) as span:
        distribution = Counter()
        for doc in documents:
            corpus = doc.metadata.get('corpus', 'unknown')
            distribution[corpus] += 1
        
        # Add distribution to span
        for corpus, count in distribution.items():
            span.set_attribute(f"corpus.{corpus}", count)
            
        return dict(distribution)

def verify_corpus_distribution(distribution: Dict[str, int], corpus_filter: Optional[str] = None) -> bool:
    """
    Verify that all documents match the corpus filter.
    
    Args:
        distribution: Dictionary with corpus distribution
        corpus_filter: Corpus to filter for, or None for all
        
    Returns:
        True if all documents match the filter, False otherwise
    """
    with create_span(
        "verify_corpus_distribution",
        attributes={
            "corpus_filter": corpus_filter or "all"
        }
    ) as span:
        # If no filter or 'all', any distribution is valid
        if not corpus_filter or corpus_filter.lower() == 'all':
            span.set_attribute("filter_verified", True)
            return True
            
        # If specific filter, all documents should be from that corpus
        total_docs = sum(distribution.values())
        filter_docs = distribution.get(corpus_filter, 0)
        
        result = filter_docs == total_docs
        span.set_attribute("filter_verified", result)
        if not result:
            logger.warning(f"Corpus filter verification failed: Expected all documents to be '{corpus_filter}', but got distribution: {distribution}")
            
        return result

def apply_corpus_filter(
    documents: List[Document], 
    corpus_filter: Optional[str] = None, 
    span: Optional[Any] = None
) -> List[Document]:
    """
    Filter documents by corpus.
    
    Args:
        documents: List of documents
        corpus_filter: Corpus to filter for, or None for all
        span: Optional parent span for telemetry
        
    Returns:
        Filtered list of documents
    """
    with create_span(
        SpanNames.DOCUMENT_FILTERING,
        attributes={
            "openinference.span.kind": OpenInferenceSpanKind.PROCESSOR,
            "corpus_filter": corpus_filter or "all",
            "initial_document_count": len(documents)
        },
        link_to_current=True
    ) as filtering_span:
        # If no filter or 'all', return all documents
        if not corpus_filter or corpus_filter.lower() == 'all':
            filtering_span.set_attribute("filtered_document_count", len(documents))
            filtering_span.set_attribute("filtering_applied", False)
            return documents
            
        # Count documents by corpus before filtering
        before_distribution = get_corpus_distribution(documents)
        for corpus, count in before_distribution.items():
            filtering_span.set_attribute(f"before.corpus.{corpus}", count)
        
        # Apply corpus filter
        before_count = len(documents)
        filtered_documents = [
            doc for doc in documents 
            if str(doc.metadata.get('corpus', '')).strip() == corpus_filter
        ]
        after_count = len(filtered_documents)
        
        # Log filtering results
        logger.debug(f"Applied corpus filter '{corpus_filter}': {before_count} → {after_count} documents")
        
        # Count documents by corpus after filtering
        after_distribution = get_corpus_distribution(filtered_documents)
        for corpus, count in after_distribution.items():
            filtering_span.set_attribute(f"after.corpus.{corpus}", count)
        
        # Add telemetry attributes
        filtering_span.set_attribute("filtered_document_count", after_count)
        filtering_span.set_attribute("filtering_applied", True)
        filtering_span.set_attribute("documents_removed", before_count - after_count)
        
        # Verify filtering worked correctly
        filtering_success = verify_corpus_distribution(after_distribution, corpus_filter)
        filtering_span.set_attribute("filtering_success", filtering_success)
        
        if not filtering_success:
            logger.warning(f"Corpus filtering may not have worked correctly. After distribution: {after_distribution}")
        
        return filtered_documents

def filter_documents_with_telemetry(
    documents: List[Document], 
    corpus_filter: Optional[str], 
    session_id: Optional[str] = None,
    qa_id: Optional[str] = None
) -> List[Document]:
    """
    Filter documents by corpus with full telemetry instrumentation.
    
    This function creates its own telemetry span and is suitable for use
    in high-level code that doesn't create spans itself.
    
    Args:
        documents: List of documents
        corpus_filter: Corpus to filter for
        session_id: Session ID for telemetry
        qa_id: QA ID for telemetry
        
    Returns:
        Filtered list of documents
    """
    with create_span(
        SpanNames.DOCUMENT_FILTERING,
        attributes={
            SpanAttributes.SESSION_ID: session_id,
            SpanAttributes.QA_ID: qa_id,
            SpanAttributes.DOCUMENT_COUNT: len(documents),
            "corpus_filter": corpus_filter or "all",
            "openinference.span.kind": OpenInferenceSpanKind.PROCESSOR
        }
    ) as span:
        # Apply corpus filter with this span as parent
        filtered_docs = apply_corpus_filter(documents, corpus_filter, span)
        
        # Document counts
        span.set_attribute(SpanAttributes.DOCUMENT_COUNT, len(filtered_docs))
        
        return filtered_docs 