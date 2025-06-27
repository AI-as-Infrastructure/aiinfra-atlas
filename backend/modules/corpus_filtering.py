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
from opentelemetry.trace import SpanKind

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
            "document_count": len(documents),
            "openinference.span.kind": OpenInferenceSpanKind.PROCESSOR
        },
        kind=OpenInferenceSpanKind.PROCESSOR,
        otel_kind=SpanKind.INTERNAL
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
            "corpus_filter": corpus_filter or "all",
            "openinference.span.kind": OpenInferenceSpanKind.PROCESSOR
        },
        kind=OpenInferenceSpanKind.PROCESSOR,
        otel_kind=SpanKind.INTERNAL
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
            logger.warning("Corpus filter verification failed")
            
        return result

def apply_corpus_filter(documents, corpus_filter, **kwargs):
    """
    Filter documents by corpus.
    
    Args:
        documents: List of documents to filter
        corpus_filter: Corpus to filter by
        **kwargs: Additional keyword arguments (ignored)
        
    Returns:
        Filtered list of documents
    """
    # If no corpus filter or "all", return all documents
    if not corpus_filter or corpus_filter.lower() == "all":
        return documents
    
    # Filter documents by corpus
    filtered_docs = []
    for doc in documents:
        if hasattr(doc, 'metadata') and 'corpus' in doc.metadata:
            if doc.metadata['corpus'] == corpus_filter:
                filtered_docs.append(doc)
    
    return filtered_docs

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
        },
        session_id=session_id,
        kind=OpenInferenceSpanKind.PROCESSOR,
        otel_kind=SpanKind.INTERNAL
    ) as span:
        # Apply filtering logic
        filtered_docs = apply_corpus_filter(documents, corpus_filter)
        
        # Create output summary for Phoenix UI
        if corpus_filter and corpus_filter.lower() != "all":
            if len(filtered_docs) != len(documents):
                output_summary = f"Applied '{corpus_filter}' filter: {len(documents)} → {len(filtered_docs)} documents"
            else:
                output_summary = f"Applied '{corpus_filter}' filter: {len(documents)} documents (no filtering needed)"
        else:
            output_summary = f"No corpus filter applied: {len(documents)} documents passed through"
        
        # Set telemetry attributes for Phoenix UI display
        span.set_attribute("documents.input_count", len(documents))
        span.set_attribute("documents.output_count", len(filtered_docs))
        span.set_attribute("documents.filtered_count", len(documents) - len(filtered_docs))
        span.set_attribute("filtering.applied", corpus_filter and corpus_filter.lower() != "all")
        span.set_attribute("corpus_filter", corpus_filter or "all")
        
        # Set Phoenix UI display attributes
        span.set_attribute("output", output_summary)
        span.set_attribute("output.value", output_summary[:500])
        span.set_attribute("summary", output_summary)
        
        # Legacy attribute for compatibility
        span.set_attribute(SpanAttributes.DOCUMENT_COUNT, len(filtered_docs))
        
        return filtered_docs 