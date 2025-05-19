"""
Document reranking utilities for ATLAS.

This module provides functions for reranking retrieved documents
to improve relevance, with built-in telemetry instrumentation.
"""

import logging
import re
from typing import List, Dict, Any, Optional, Tuple, Union, Callable
from datetime import datetime

from langchain_core.documents.base import Document

# Import telemetry modules
from backend.telemetry.core import create_span, SpanKind
from backend.telemetry.constants import SpanAttributes, SpanNames, OpenInferenceSpanKind

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

def enhance_document_relevance(
    documents: List[Document], 
    query: str, 
    max_docs: int = DEFAULT_MAX_DOCS,
    session_id: Optional[str] = None,
    qa_id: Optional[str] = None
) -> List[Document]:
    """
    Enhance document relevance by reranking based on query relevance.
    
    This function reranks documents based on their calculated relevance
    to the query, potentially improving the order compared to pure
    vector similarity.
    
    Args:
        documents: List of documents to rerank
        query: Original query string
        max_docs: Maximum number of documents to return after reranking
        session_id: Session ID for telemetry
        qa_id: Question/Answer ID for telemetry
        
    Returns:
        Reranked list of documents (limited to max_docs)
    """
    # Use telemetry to track reranking
    with create_span(
        SpanNames.DOCUMENT_RERANKING,
        attributes={
            # Session identifiers
            SpanAttributes.SESSION_ID: session_id,
            SpanAttributes.QA_ID: qa_id,
            
            # Input information
            "input.value": query,
            "input.documents_count": len(documents),
            
            # Reranking details
            "description": f"Reranking {len(documents)} documents for optimal relevance",
            "operation": "document_reranking",
            "max_docs": max_docs,
            SpanAttributes.DOCUMENT_COUNT: len(documents),
            
            # Critical: Set the kind in formats Phoenix will recognize
            "type": "RERANKER",
            "span_kind": "RERANKER",
            "otel.kind": "PROCESSOR", 
            "openinference.span.kind": "RERANKER",
            
            # Additional metadata
            "reranker.type": "query_relevance",
            "reranker.config": {
                "weight_exact_match": WEIGHT_EXACT_MATCH,
                "weight_keyword_freq": WEIGHT_KEYWORD_FREQ,
                "weight_proximity": WEIGHT_PROXIMITY,
                "exact_match_score": EXACT_MATCH_SCORE,
                "max_keyword_score": MAX_KEYWORD_SCORE,
                "proximity_window": PROXIMITY_WINDOW,
                "metadata_match_bonus": METADATA_MATCH_BONUS,
                "max_score": MAX_SCORE
            },
            "reranker.description": "Reranks documents based on query term relevance and metadata matches"
        },
        kind=SpanKind.INTERNAL,
        link_to_current=True
    ) as reranking_span:
        try:
            start_time = datetime.now()
            
            # Skip reranking if no documents
            if not documents:
                reranking_span.set_attribute("reranked", False)
                reranking_span.set_attribute("reason", "no_documents")
                return []
                
            # Skip reranking if only one document
            if len(documents) <= 1:
                reranking_span.set_attribute("reranked", False)
                reranking_span.set_attribute("reason", "single_document")
                return documents
                
            # Calculate relevance scores for each document
            docs_with_scores = []
            for idx, doc in enumerate(documents):
                score = calculate_relevance_score(doc, query)
                docs_with_scores.append((doc, score))
                
                # For metrics, track first few documents' scores
                if idx < 10:  # Limit to avoid too many attributes
                    doc_id = getattr(doc, 'id', None) or getattr(doc.metadata, 'id', f"doc_{idx}")
                    reranking_span.set_attribute(f"document.{idx}.id", str(doc_id))
                    reranking_span.set_attribute(f"document.{idx}.score", score)
            
            # Sort by score in descending order
            docs_with_scores.sort(key=lambda x: x[1], reverse=True)
            
            # Limit to max_docs
            docs_with_scores = docs_with_scores[:max_docs]
            
            # Extract just the documents
            reranked_docs = [doc for doc, _ in docs_with_scores]
            
            # Record metrics
            reranking_time = (datetime.now() - start_time).total_seconds()
            reranking_span.set_attribute("reranking_time_seconds", reranking_time)
            reranking_span.set_attribute("reranked", True)
            reranking_span.set_attribute("input_document_count", len(documents))
            reranking_span.set_attribute("output_document_count", len(reranked_docs))
            
            # Log distribution of scores
            all_scores = [score for _, score in docs_with_scores]
            if all_scores:
                reranking_span.set_attribute("max_score", max(all_scores))
                reranking_span.set_attribute("min_score", min(all_scores))
                reranking_span.set_attribute("avg_score", sum(all_scores) / len(all_scores))
            
            # Set output for Phoenix display
            reranking_summary = f"Reranked {len(documents)} docs → {len(reranked_docs)} results in {reranking_time:.2f}s"
            
            # Set all output attributes directly on the main span
            reranking_span.set_attribute("content", reranking_summary)
            
            # Set using the output method if available
            if hasattr(reranking_span, "set_output"):
                reranking_span.set_output(reranking_summary)
            
            # Also set standard output attributes for maximum compatibility
            reranking_span.set_attribute("output", reranking_summary)
            reranking_span.set_attribute("output.value", reranking_summary)
            reranking_span.set_attribute(SpanAttributes.OUTPUT, reranking_summary)
            
            return reranked_docs
            
        except Exception as e:
            # Record error in telemetry
            reranking_span.record_exception(e)
            reranking_span.set_attribute("reranking_error", str(e))
            
            # Log the error
            logger.error(f"Error during document reranking: {e}", exc_info=True)
            
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
    
    This function is the primary entry point for document reranking
    that ensures proper telemetry is recorded.
    
    Args:
        documents: List of documents to rerank
        query: Original query string
        session_id: Session ID for telemetry
        qa_id: Question/Answer ID for telemetry
        max_docs: Maximum number of documents to return
        
    Returns:
        Reranked list of documents
    """
    logger.info(f"Reranking {len(documents)} documents for query: {query[:50]}...")
    
    try:
        # Call the enhanced document relevance function with telemetry
        reranked_docs = enhance_document_relevance(
            documents=documents,
            query=query,
            max_docs=max_docs,
            session_id=session_id,
            qa_id=qa_id
        )
        
        logger.info(f"Reranking complete. Returning {len(reranked_docs)} documents.")
        return reranked_docs
        
    except Exception as e:
        logger.error(f"Error in document reranking: {e}", exc_info=True)
        
        # Return original documents as fallback (limited to max_docs)
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