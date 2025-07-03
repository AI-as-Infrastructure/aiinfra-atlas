"""
Document reranking utilities for ATLAS.

This module provides functions for reranking retrieved documents
to improve relevance, with built-in telemetry instrumentation.
"""

import logging
import re
from typing import List, Dict, Any, Optional, Tuple, Union, Callable
from datetime import datetime
from contextlib import contextmanager
import time
import json

from langchain_core.documents.base import Document

# Import telemetry modules
from backend.telemetry.core import create_span
from backend.telemetry.constants import SpanAttributes, SpanNames, OpenInferenceSpanKind
from backend.telemetry import set_span_outputs
from opentelemetry.trace import SpanKind
from opentelemetry.trace import Status, StatusCode

logger = logging.getLogger(__name__)

#----------------------------------------------------------------------
# COMPILED REGEX PATTERNS - Pre-compiled for performance
#----------------------------------------------------------------------
WORD_PATTERN = re.compile(r'\b\w+\b')
KEYWORD_PATTERN_CACHE = {}  # Cache for compiled keyword patterns
PROXIMITY_PATTERN_CACHE = {}  # Cache for compiled proximity patterns

def get_keyword_pattern(keyword: str) -> re.Pattern:
    """Get or create a compiled regex pattern for a keyword."""
    if keyword not in KEYWORD_PATTERN_CACHE:
        KEYWORD_PATTERN_CACHE[keyword] = re.compile(r'\b' + re.escape(keyword) + r'\b')
    return KEYWORD_PATTERN_CACHE[keyword]

def get_proximity_pattern(kw1: str, kw2: str, window: int) -> re.Pattern:
    """Get or create a compiled regex pattern for keyword proximity."""
    key = f"{kw1}_{kw2}_{window}"
    if key not in PROXIMITY_PATTERN_CACHE:
        pattern = r'\b' + re.escape(kw1) + r'(.{0,' + str(window) + r'})' + re.escape(kw2) + r'\b'
        PROXIMITY_PATTERN_CACHE[key] = re.compile(pattern)
    return PROXIMITY_PATTERN_CACHE[key]

#----------------------------------------------------------------------
# RERANKING CONFIGURATION - Adjust these values to calibrate behavior
#----------------------------------------------------------------------

# Scoring weights (must sum to 1.0)
WEIGHT_EXACT_MATCH = 0.5    # Weight for exact phrase matches
WEIGHT_KEYWORD_FREQ = 0.3   # Weight for keyword frequency
WEIGHT_PROXIMITY = 0.2      # Weight for keyword proximity

# Scoring parameters
EXACT_MATCH_SCORE = 10.0    # Score awarded for exact phrase match
MAX_KEYWORD_SCORE = 5.0     # Maximum score per keyword
PROXIMITY_WINDOW = 50       # Character window for proximity detection
METADATA_MATCH_BONUS = 0.5  # Score bonus for each metadata field match
MAX_SCORE = 10.0            # Maximum total score (for normalization)

# Filtering parameters
MIN_TERM_LENGTH = 3         # Minimum length for keywords to be considered
MAX_PREVIEW_CHARS = 300     # Maximum characters to include in text previews
DEFAULT_MAX_DOCS = 10       # Default number of documents to return after reranking

# Common English stop words to ignore when extracting keywords
STOP_WORDS = {
    'a', 'an', 'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 
    'for', 'with', 'by', 'about', 'as', 'is', 'are', 'was', 'were',
    'has', 'have', 'had', 'be', 'been', 'being', 'of', 'from', 'it'
}

#----------------------------------------------------------------------

@contextmanager
def trace_document_reranking(
    documents: List[Document],
    query: str,
    session_id: Optional[str] = None,
    qa_id: Optional[str] = None,
    max_docs: int = DEFAULT_MAX_DOCS
):
    """
    Context manager to create a reranking span with proper telemetry attributes.
    
    This function wraps the reranking operation in a telemetry span that 
    captures detailed metrics about the reranking process.
    
    Args:
        documents: List of documents to rerank
        query: Original query string
        session_id: Session ID for telemetry
        qa_id: Question/Answer ID for telemetry
        max_docs: Maximum number of documents to return
        
    Yields:
        The reranking span
    """
    with create_span(
        SpanNames.DOCUMENT_RERANKING,
        attributes={
            # Core identification attributes
            SpanAttributes.SESSION_ID: session_id,
            SpanAttributes.QA_ID: qa_id,
            
            # Input info using standard format
            SpanAttributes.INPUT_VALUE: query,
            SpanAttributes.DOCUMENT_COUNT: len(documents),
            
            # Span categorization
            "openinference.span.kind": OpenInferenceSpanKind.RERANKER,
        },
        session_id=session_id,  # Critical for session association
        kind=OpenInferenceSpanKind.RERANKER,
        otel_kind=SpanKind.INTERNAL
    ) as span:
        try:
            # Record start time
            start_time = time.time()
            
            # Yield the span to the caller
            yield span
            
            # Calculate processing time
            elapsed_time = time.time() - start_time
            
            # Set standard outputs using direct span attributes
            summary = f"Reranked {len(documents)} documents by relevance"
            span.set_attribute("summary", summary)
            span.set_attribute("output", summary)
            span.set_attribute("output.value", summary[:500])
            span.set_attribute("openinference.span.kind", OpenInferenceSpanKind.RERANKER)
            span.set_attribute("processing_time_seconds", elapsed_time)
            span.set_attribute("max_docs", max_docs)
            span.set_attribute("input_document_count", len(documents))
            
        except Exception as e:
            # Handle error using direct span attributes
            error_summary = f"Error reranking documents: {str(e)}"
            span.set_attribute("summary", error_summary)
            span.set_attribute("output", error_summary)
            span.set_attribute("output.value", error_summary[:500])
            span.set_attribute("openinference.span.kind", OpenInferenceSpanKind.RERANKER)
            span.set_attribute("error", str(e))
            span.set_status(Status(StatusCode.ERROR, str(e)))
            logger.error(f"Error during document reranking: {e}", exc_info=True)
            raise

def calculate_relevance_score(document: Document, query: str) -> float:
    """
    Calculate a relevance score for a document based on the query.
    
    This function implements a simple relevance scoring algorithm that considers:
    1. Exact phrase matches (highest weight)
    2. Keyword frequency (medium weight)
    3. Word proximity (lower weight)
    
    Args:
        document: Document to score
        query: The original query string
        
    Returns:
        A relevance score (higher is more relevant)
    """
    if not document or not hasattr(document, 'page_content'):
        return 0.0
        
    content = document.page_content.lower()
    query_lower = query.lower()
    
    # Extract meaningful keywords (ignoring common stop words)
    keywords = [word for word in WORD_PATTERN.findall(query_lower) 
                if word not in STOP_WORDS and len(word) >= MIN_TERM_LENGTH]
    
    # 1. Exact phrase match (highest weight)
    phrase_score = EXACT_MATCH_SCORE if query_lower in content else 0.0
    
    # 2. Keyword frequency
    keyword_score = 0.0
    for keyword in keywords:
        pattern = get_keyword_pattern(keyword)
        count = len(pattern.findall(content))
        # More occurrences increase score, but with diminishing returns
        keyword_score += min(MAX_KEYWORD_SCORE, count * 1.0)  # Cap per keyword
    
    # 3. Word proximity (are keywords close to each other?)
    proximity_score = 0.0
    if len(keywords) > 1:
        # Check if keywords appear within proximity window
        for i, kw1 in enumerate(keywords[:-1]):
            for kw2 in keywords[i+1:]:
                # Look for patterns where keywords are close
                pattern1 = get_proximity_pattern(kw1, kw2, PROXIMITY_WINDOW)
                if pattern1.search(content):
                    proximity_score += 1.0
                # Check reverse order too
                pattern2 = get_proximity_pattern(kw2, kw1, PROXIMITY_WINDOW)
                if pattern2.search(content):
                    proximity_score += 1.0
    
    # Combine scores with appropriate weights
    total_score = (
        phrase_score * WEIGHT_EXACT_MATCH +
        keyword_score * WEIGHT_KEYWORD_FREQ +
        proximity_score * WEIGHT_PROXIMITY
    )
    
    # Apply a boost for metadata matches if available
    if hasattr(document, 'metadata'):
        metadata_boost = 0.0
        for key, value in document.metadata.items():
            if isinstance(value, str) and any(kw in value.lower() for kw in keywords):
                metadata_boost += METADATA_MATCH_BONUS  # Bonus for each metadata field with keyword match
        total_score += metadata_boost
        
    # Normalize score to MAX_SCORE range for easier interpretation
    normalized_score = min(MAX_SCORE, total_score)
    
    return normalized_score

def _rerank_documents_internal(
    documents: List[Document],
    query: str,
    max_docs: int = DEFAULT_MAX_DOCS
) -> Tuple[List[Document], List[float]]:
    """
    Internal function that performs the actual document reranking without telemetry.
    
    Args:
        documents: List of documents to rerank
        query: Original query string
        max_docs: Maximum documents to return
        
    Returns:
        Reranked list of documents and their scores
    """
    if not documents:
        return [], []
        
    if not query or len(query.strip()) == 0:
        return documents[:max_docs], [0.0] * min(len(documents), max_docs)
    
    # Calculate relevance scores for each document in batches
    scored_docs = []
    batch_size = 50  # Process documents in batches to yield control
    
    for i in range(0, len(documents), batch_size):
        batch = documents[i:i + batch_size]
        batch_scores = []
        
        # Process batch
        for doc in batch:
            score = calculate_relevance_score(doc, query)
            batch_scores.append((doc, score))
        
        scored_docs.extend(batch_scores)
        
        # Brief pause to allow other threads to run
        if i > 0 and i % (batch_size * 2) == 0:
            import time
            time.sleep(0.001)  # 1ms pause to yield to other threads
    
    # Sort by score (descending)
    scored_docs.sort(key=lambda x: x[1], reverse=True)
    
    # Limit to max_docs
    scored_docs = scored_docs[:max_docs]
    
    # Extract documents and scores separately
    reranked_docs = [doc for doc, _ in scored_docs]
    scores = [score for _, score in scored_docs]
    
    # Return the reranked documents and their scores
    return reranked_docs, scores

def enhance_document_relevance(
    documents: List[Document], 
    query: str, 
    max_docs: int = DEFAULT_MAX_DOCS,
    session_id: Optional[str] = None,
    qa_id: Optional[str] = None,
    create_span: bool = True
) -> List[Document]:
    """
    Enhance document relevance based on query-specific scoring.
    
    This function reranks documents by calculating a relevance score for each 
    document based on exact matches, keyword frequency, and term proximity.
    
    Args:
        documents: List of documents to rerank
        query: Original query string
        max_docs: Maximum number of documents to return
        session_id: Session ID for telemetry
        qa_id: Question/Answer ID for telemetry
        create_span: Whether to create a telemetry span (set to False if called 
                     from a function that already creates a span)
        
    Returns:
        Reranked list of documents
    """
    # Skip creating a redundant span if called from a function that already created one
    if not create_span:
        reranked_docs, _ = _rerank_documents_internal(documents, query, max_docs)
        return reranked_docs
    
    # Create a telemetry span for the reranking operation
    with trace_document_reranking(
        documents=documents,
        query=query,
        session_id=session_id,
        qa_id=qa_id,
        max_docs=max_docs
    ) as span:
        try:
            # Skip reranking if no documents
            if not documents:
                span.set_attribute("status", "no_documents")
                
                # Set output using direct span attributes
                empty_message = "No documents to rerank"
                span.set_attribute("summary", empty_message)
                span.set_attribute("output", empty_message)
                span.set_attribute("output.value", empty_message[:500])
                span.set_attribute("openinference.span.kind", OpenInferenceSpanKind.RERANKER)
                    
                return []
                
            # Skip reranking if empty query
            if not query or len(query.strip()) == 0:
                span.set_attribute("status", "empty_query")
                
                # Set output using direct span attributes
                skip_message = "Empty query, returning original documents"
                span.set_attribute("summary", skip_message)
                span.set_attribute("output", skip_message)
                span.set_attribute("output.value", skip_message[:500])
                span.set_attribute("openinference.span.kind", OpenInferenceSpanKind.RERANKER)
                
                return documents[:max_docs]
            
            # Call the internal reranking function
            reranked_docs, scores = _rerank_documents_internal(documents, query, max_docs)
            
            # Log score information if available
            if scores and len(scores) > 0:
                min_score = min(scores)
                max_score = max(scores)
                avg_score = sum(scores) / len(scores)
                
                span.set_attribute("score.min", min_score)
                span.set_attribute("score.max", max_score)
                span.set_attribute("score.avg", avg_score)
                
                # Add scores for top 3 documents
                for i, score in enumerate(scores[:3]):
                    span.set_attribute(f"top_score.{i+1}", score)
            
            # Set standardized output using direct span attributes
            summary = f"Reranked {len(documents)} → {len(reranked_docs)} documents"
            
            # Create details dictionary
            details = {
                "input_document_count": len(documents),
                "output_document_count": len(reranked_docs),
                "max_docs": max_docs
            }
            
            # Add score information to details
            if scores and len(scores) > 0:
                details["score_min"] = min_score
                details["score_max"] = max_score
                details["score_avg"] = avg_score
                details["score_range"] = f"{min_score:.2f}-{max_score:.2f}"
            
            # Set standard outputs using direct span attributes
            span.set_attribute("summary", summary)
            span.set_attribute("output", summary)
            span.set_attribute("output.value", summary[:500])
            span.set_attribute("openinference.span.kind", OpenInferenceSpanKind.RERANKER)
            for key, value in details.items():
                span.set_attribute(key, value)
            
            # Add document previews
            if reranked_docs:
                for i, doc in enumerate(reranked_docs[:3]):
                    span.set_attribute(f"document_{i}_preview", doc.page_content[:200])
            
            
            return reranked_docs
            
        except Exception as e:
            logger.error(f"Error during document reranking: {e}", exc_info=True)
            
            # Set error using direct span attributes
            error_message = f"Reranking error: {str(e)}"
            span.set_attribute("summary", error_message)
            span.set_attribute("output", error_message)
            span.set_attribute("output.value", error_message[:500])
            span.set_attribute("openinference.span.kind", OpenInferenceSpanKind.RERANKER)
            span.set_attribute("error", str(e))
            span.set_status(Status(StatusCode.ERROR, str(e)))
            
            # Return original documents as fallback
            return documents[:max_docs]

def rerank_documents_with_telemetry(
    documents: List[Document],
    query: str,
    session_id: Optional[str] = None,
    qa_id: Optional[str] = None,
    max_docs: int = DEFAULT_MAX_DOCS
) -> List[Document]:
    """
    Rerank documents with telemetry instrumentation.
    
    Args:
        documents: List of documents to rerank
        query: Query string for relevance scoring
        session_id: Session ID for telemetry
        qa_id: QA ID for telemetry
        max_docs: Maximum number of documents to return
    
    Returns:
        Reranked documents
    """
    # Use trace_operation for consistent span creation (like other functions)
    from backend.telemetry.spans import trace_operation
    from opentelemetry.trace import Status, StatusCode
    
    with trace_operation(
        SpanNames.DOCUMENT_RERANKING,
        attributes={
            # Core identification attributes
            SpanAttributes.INPUT_VALUE: query,
            SpanAttributes.DOCUMENT_COUNT: len(documents),
            
            # OpenInference standard reranker attributes
            "reranker.query": query,
            "reranker.input_documents": [
                {
                    "document.content": doc.page_content,
                    "document.metadata": getattr(doc, 'metadata', {})
                } for doc in documents
            ],
        },
        session_id=session_id,
        qa_id=qa_id,
        openinference_kind=OpenInferenceSpanKind.RERANKER,
        input_data=query
    ) as span:
        try:
            # Perform actual reranking logic directly (no nested span creation)
            reranked_docs, scores = _rerank_documents_internal(documents, query, max_docs)
            
            # Add OpenInference standard output documents
            span.set_attribute("reranker.output_documents", [
                {
                    "document.content": doc.page_content,
                    "document.metadata": getattr(doc, 'metadata', {}),
                    "document.score": scores[i] if i < len(scores) else 0.0
                } for i, doc in enumerate(reranked_docs)
            ])
            
            # Add reranker parameters
            span.set_attribute("reranker.top_k", max_docs)
            span.set_attribute("reranker.model_name", "bm25_custom")  # Our internal scoring algorithm
            
            # Add score information as attributes
            if scores and len(scores) > 0:
                min_score = min(scores)
                max_score = max(scores)
                avg_score = sum(scores) / len(scores)
                
                span.set_attribute("score.min", min_score)
                span.set_attribute("score.max", max_score)
                span.set_attribute("score.avg", avg_score)
            
            # Add document previews with flat attribute names
            for i, doc in enumerate(reranked_docs[:3]):
                if hasattr(doc, 'page_content'):
                    content = doc.page_content[:200]
                    if len(doc.page_content) > 200:
                        content += "..."
                    span.set_attribute(f"doc_{i}_preview", content)
                    
                # Add metadata with flat attribute names
                if hasattr(doc, 'metadata'):
                    for key, value in doc.metadata.items():
                        # Limit to important metadata fields
                        if key in ["date", "corpus", "title", "source"]:
                            # Ensure value is a string
                            span.set_attribute(f"doc_{i}_{key}", str(value))
            
            # Set standard outputs using direct span attributes (consistent with other functions)
            summary = f"Reranked {len(documents)} → {len(reranked_docs)} documents"
            span.set_attribute("summary", summary)
            span.set_attribute("output", summary)
            span.set_attribute("output.value", summary[:500])
            span.set_attribute("input_document_count", len(documents))
            span.set_attribute("output_document_count", len(reranked_docs))
            span.set_attribute("max_docs", max_docs)
            
            return reranked_docs
            
        except Exception as e:
            logger.error(f"Error in document reranking: {e}", exc_info=True)
            
            # Set error information on span using direct attributes (consistent with other functions)
            error_summary = f"Error in document reranking: {str(e)}"
            span.set_attribute("summary", error_summary)
            span.set_attribute("output", error_summary)
            span.set_attribute("output.value", error_summary[:500])
            span.set_attribute("error", str(e))
            span.set_status(Status(StatusCode.ERROR, str(e)))
            
            # Return original documents as fallback
            return documents[:max_docs]

def configure_reranker(config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Configure the reranker with custom parameters.
    
    This function allows dynamic adjustment of the reranking algorithm's
    parameters without modifying the module code. It updates global
    configuration variables based on the provided config dictionary.
    
    Args:
        config: Dictionary containing configuration parameters to update
        
    Returns:
        Dictionary with the updated configuration values
    """
    global WEIGHT_EXACT_MATCH, WEIGHT_KEYWORD_FREQ, WEIGHT_PROXIMITY
    global EXACT_MATCH_SCORE, MAX_KEYWORD_SCORE, PROXIMITY_WINDOW
    global METADATA_MATCH_BONUS, MAX_SCORE, MIN_TERM_LENGTH
    global DEFAULT_MAX_DOCS, MAX_PREVIEW_CHARS
    
    # Create a dictionary with current configuration
    current_config = {
        "weight_exact_match": WEIGHT_EXACT_MATCH,
        "weight_keyword_freq": WEIGHT_KEYWORD_FREQ, 
        "weight_proximity": WEIGHT_PROXIMITY,
        "exact_match_score": EXACT_MATCH_SCORE,
        "max_keyword_score": MAX_KEYWORD_SCORE,
        "proximity_window": PROXIMITY_WINDOW,
        "metadata_match_bonus": METADATA_MATCH_BONUS,
        "max_score": MAX_SCORE,
        "min_term_length": MIN_TERM_LENGTH,
        "default_max_docs": DEFAULT_MAX_DOCS,
        "max_preview_chars": MAX_PREVIEW_CHARS
    }
    
    # Update only the provided configuration parameters
    if config:
        # Update scoring weights
        if "weight_exact_match" in config:
            WEIGHT_EXACT_MATCH = float(config["weight_exact_match"])
        if "weight_keyword_freq" in config:
            WEIGHT_KEYWORD_FREQ = float(config["weight_keyword_freq"])
        if "weight_proximity" in config:
            WEIGHT_PROXIMITY = float(config["weight_proximity"])
            
        # Update scoring parameters
        if "exact_match_score" in config:
            EXACT_MATCH_SCORE = float(config["exact_match_score"])
        if "max_keyword_score" in config:
            MAX_KEYWORD_SCORE = float(config["max_keyword_score"])
        if "proximity_window" in config:
            PROXIMITY_WINDOW = int(config["proximity_window"])
        if "metadata_match_bonus" in config:
            METADATA_MATCH_BONUS = float(config["metadata_match_bonus"])
        if "max_score" in config:
            MAX_SCORE = float(config["max_score"])
            
        # Update filtering parameters
        if "min_term_length" in config:
            MIN_TERM_LENGTH = int(config["min_term_length"])
        if "default_max_docs" in config:
            DEFAULT_MAX_DOCS = int(config["default_max_docs"])
        if "max_preview_chars" in config:
            MAX_PREVIEW_CHARS = int(config["max_preview_chars"])
            
        # Validate weights sum to approximately 1.0
        weights_sum = WEIGHT_EXACT_MATCH + WEIGHT_KEYWORD_FREQ + WEIGHT_PROXIMITY
        if abs(weights_sum - 1.0) > 0.01:
            logger.warning(f"Reranker weights sum to {weights_sum}, not 1.0. This may produce unexpected results.")
    
    # Return the updated configuration
    updated_config = {
        "weight_exact_match": WEIGHT_EXACT_MATCH,
        "weight_keyword_freq": WEIGHT_KEYWORD_FREQ, 
        "weight_proximity": WEIGHT_PROXIMITY,
        "exact_match_score": EXACT_MATCH_SCORE,
        "max_keyword_score": MAX_KEYWORD_SCORE,
        "proximity_window": PROXIMITY_WINDOW,
        "metadata_match_bonus": METADATA_MATCH_BONUS,
        "max_score": MAX_SCORE,
        "min_term_length": MIN_TERM_LENGTH,
        "default_max_docs": DEFAULT_MAX_DOCS,
        "max_preview_chars": MAX_PREVIEW_CHARS
    }
    
    return updated_config

def rerank_documents(documents: List[Document], query: str, max_docs: int = DEFAULT_MAX_DOCS) -> List[Document]:
    """
    Simple reranking function without telemetry (used by HansardRetriever).
    
    This function provides a clean interface for document reranking without
    creating additional telemetry spans, making it suitable for use within
    other components that already have their own telemetry.
    
    Args:
        documents: List of documents to rerank
        query: Query string for relevance scoring
        max_docs: Maximum number of documents to return
        
    Returns:
        Reranked list of documents
    """
    # Use the internal implementation directly without creating telemetry spans
    reranked_docs, _ = _rerank_documents_internal(documents, query, max_docs)
    return reranked_docs