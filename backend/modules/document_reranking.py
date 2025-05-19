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
from backend.telemetry.core import create_span, SpanKind
from backend.telemetry.constants import SpanAttributes, SpanNames, OpenInferenceSpanKind
from backend.telemetry import BaseSpanManager, get_span_manager, RAGSpanManager

logger = logging.getLogger(__name__)

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
        kind=SpanKind.INTERNAL,
        link_to_current=True
    ) as span:
        try:
            # Record start time
            start_time = time.time()
            
            # Yield the span to the caller
            yield span
            
            # Calculate processing time
            elapsed_time = time.time() - start_time
            
            # Set standard outputs using BaseSpanManager
            summary = f"Reranked {len(documents)} documents by relevance"
            BaseSpanManager.set_standard_outputs(
                span=span,
                summary=summary,
                details={
                    "processing_time_seconds": elapsed_time,
                    "max_docs": max_docs,
                    "input_document_count": len(documents)
                },
                span_kind=OpenInferenceSpanKind.RERANKER
            )
            
        except Exception as e:
            # Handle error using BaseSpanManager
            error_summary = f"Error reranking documents: {str(e)}"
            BaseSpanManager.set_standard_outputs(
                span=span,
                summary=error_summary,
                error=e,
                span_kind=OpenInferenceSpanKind.RERANKER
            )
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
    keywords = [word for word in re.findall(r'\b\w+\b', query_lower) 
                if word not in STOP_WORDS and len(word) >= MIN_TERM_LENGTH]
    
    # 1. Exact phrase match (highest weight)
    phrase_score = EXACT_MATCH_SCORE if query_lower in content else 0.0
    
    # 2. Keyword frequency
    keyword_score = 0.0
    for keyword in keywords:
        count = len(re.findall(r'\b' + re.escape(keyword) + r'\b', content))
        # More occurrences increase score, but with diminishing returns
        keyword_score += min(MAX_KEYWORD_SCORE, count * 1.0)  # Cap per keyword
    
    # 3. Word proximity (are keywords close to each other?)
    proximity_score = 0.0
    if len(keywords) > 1:
        # Check if keywords appear within proximity window
        for i, kw1 in enumerate(keywords[:-1]):
            for kw2 in keywords[i+1:]:
                # Look for patterns where keywords are close
                pattern = r'\b' + re.escape(kw1) + r'(.{0,' + str(PROXIMITY_WINDOW) + r'})' + re.escape(kw2) + r'\b'
                if re.search(pattern, content):
                    proximity_score += 1.0
                # Check reverse order too
                pattern = r'\b' + re.escape(kw2) + r'(.{0,' + str(PROXIMITY_WINDOW) + r'})' + re.escape(kw1) + r'\b'
                if re.search(pattern, content):
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
    
    # Calculate relevance scores for each document
    scored_docs = []
    for doc in documents:
        score = calculate_relevance_score(doc, query)
        scored_docs.append((doc, score))
    
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
                
                # Set output using the BaseSpanManager
                empty_message = "No documents to rerank"
                BaseSpanManager.set_standard_outputs(
                    span=span,
                    summary=empty_message,
                    span_kind=OpenInferenceSpanKind.RERANKER
                )
                    
                return []
                
            # Skip reranking if empty query
            if not query or len(query.strip()) == 0:
                span.set_attribute("status", "empty_query")
                
                # Set output using the BaseSpanManager
                skip_message = "Empty query, returning original documents"
                BaseSpanManager.set_standard_outputs(
                    span=span,
                    summary=skip_message,
                    span_kind=OpenInferenceSpanKind.RERANKER
                )
                
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
            
            # Set standardized output using BaseSpanManager
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
            
            # Set standard outputs
            BaseSpanManager.set_standard_outputs(
                span=span,
                summary=summary,
                details=details,
                span_kind=OpenInferenceSpanKind.RERANKER
            )
            
            # Add document previews using BaseSpanManager
            if reranked_docs:
                BaseSpanManager.add_document_preview(span, reranked_docs)
            
            # Log completion
            logger.info(f"Document reranking complete: {summary}")
            
            return reranked_docs
            
        except Exception as e:
            logger.error(f"Error during document reranking: {e}", exc_info=True)
            
            # Set error using BaseSpanManager
            error_message = f"Reranking error: {str(e)}"
            BaseSpanManager.set_standard_outputs(
                span=span,
                summary=error_message,
                error=e,
                span_kind=OpenInferenceSpanKind.RERANKER
            )
            
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
    Rerank documents with consistent telemetry.
    
    Args:
        documents: Documents to rerank
        query: Query text
        session_id: Session ID
        qa_id: Question/Answer ID
        max_docs: Maximum documents to return
    
    Returns:
        Reranked documents
    """
    # Create a span manager for ranking
    span_manager = get_span_manager("document_reranking", RAGSpanManager)
    
    # Use standard attribute approach with proper separation of info vs attributes
    with span_manager.ranking_span(
        document_count=len(documents),
        session_id=session_id,
        qa_id=qa_id,
    ) as span:
        try:
            # Add query and max_docs as regular attributes
            span.set_attribute("query", query)
            span.set_attribute("max_docs", str(max_docs))
            span.set_attribute("reranker_type", "bm25")
            
            # Perform actual reranking logic
            reranked_docs, scores = _rerank_documents_internal(documents, query, max_docs)
            
            # Update span with results in attributes section
            span.set_attribute("reranked_document_count", len(reranked_docs))
            
            # Add score information to attributes where it belongs
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
            
            return reranked_docs
            
        except Exception as e:
            logger.error(f"Error in document reranking: {e}", exc_info=True)
            span.record_exception(e)
            span.set_attribute("error", str(e))
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
            
        logger.info(f"Reranker configuration updated: {config}")
    
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