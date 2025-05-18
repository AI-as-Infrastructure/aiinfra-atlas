"""
Quality evaluation for LLM responses.

This module provides functions to evaluate the quality of LLM responses
in terms of relevance, factual accuracy, citation coverage, and completeness.
"""

import logging
from typing import Dict, Any, List, Optional
from langchain_core.documents.base import Document

logger = logging.getLogger(__name__)

def evaluate_response_quality(
    question: str,
    response: str,
    documents: List[Document]
) -> Optional[Dict[str, float]]:
    """
    Evaluate the quality of an LLM response based on key metrics.
    
    This is a placeholder implementation that returns simple heuristic-based metrics.
    In a production implementation, this would use a more sophisticated approach,
    potentially with an LLM-based evaluator for more accurate assessment.
    
    Args:
        question: The user's question
        response: The LLM's response
        documents: The documents used to generate the response
        
    Returns:
        Dictionary of quality metrics or None if evaluation fails
    """
    try:
        # Empty metrics dict
        metrics = {}
        
        # Calculate relevance - check for question terms in response
        relevance_score = calculate_relevance(question, response)
        metrics["relevance_score"] = relevance_score
        
        # Calculate factual accuracy based on document overlap
        factual_accuracy = calculate_accuracy(response, documents)
        metrics["factual_accuracy"] = factual_accuracy
        
        # Calculate citation coverage
        citation_coverage = calculate_coverage(response, documents)
        metrics["citation_coverage"] = citation_coverage
        
        # Calculate completeness - how well the response addresses the question
        completeness = calculate_completeness(question, response)
        metrics["response_completeness"] = completeness
        
        # Calculate overall score (weighted average)
        overall_score = (
            relevance_score * 0.3 +
            factual_accuracy * 0.3 +
            citation_coverage * 0.2 +
            completeness * 0.2
        )
        metrics["overall_quality_score"] = overall_score
        
        return metrics
    
    except Exception as e:
        logger.error(f"Error evaluating response quality: {e}", exc_info=True)
        return None

def calculate_relevance(question: str, response: str) -> float:
    """
    Calculate relevance of response to question.
    
    Args:
        question: User question
        response: LLM response
        
    Returns:
        Float relevance score (0.0-1.0)
    """
    # Simple heuristic: Check what percentage of question terms appear in response
    # In a production system, use embeddings similarity or proper natural language understanding
    try:
        # Get unique normalized terms from question
        question_terms = set(question.lower().split())
        
        # Remove common stopwords
        stopwords = {"the", "a", "an", "and", "or", "but", "is", "are", "was", "were", "in", "on", "at", "to", "for"}
        question_terms = question_terms - stopwords
        
        if not question_terms:
            return 0.9  # If no significant terms, default to high relevance
        
        # See how many question terms appear in response
        response_lower = response.lower()
        terms_found = sum(1 for term in question_terms if term in response_lower)
        
        # Calculate relevance score
        relevance = min(1.0, terms_found / len(question_terms))
        
        return relevance
    except Exception as e:
        logger.error(f"Error calculating relevance: {e}")
        return 0.5  # Default to neutral score on error

def calculate_accuracy(response: str, documents: List[Document]) -> float:
    """
    Calculate factual accuracy of response based on source documents.
    
    Args:
        response: LLM response
        documents: Source documents
        
    Returns:
        Float accuracy score (0.0-1.0)
    """
    try:
        # Simple heuristic: Check how many document sentences appear in the response
        # In production, use NLU to check for claim verification and entailment
        
        # Get all document text
        all_doc_text = " ".join([doc.page_content for doc in documents])
        
        # Count sentences in documents and response
        doc_sentences = all_doc_text.split(".")
        response_sentences = response.split(".")
        
        # Count sentences with significant overlap
        supported_sentences = 0
        for resp_sentence in response_sentences:
            if not resp_sentence.strip():
                continue
                
            # Check for significant overlap with any document sentence
            resp_words = set(resp_sentence.lower().split())
            if len(resp_words) < 3:
                continue  # Skip very short sentences
                
            for doc_sentence in doc_sentences:
                doc_words = set(doc_sentence.lower().split())
                if len(doc_words) < 3:
                    continue
                
                # Calculate word overlap
                common_words = resp_words.intersection(doc_words)
                if len(common_words) / len(resp_words) > 0.3:  # If 30% of words match
                    supported_sentences += 1
                    break
        
        # Calculate accuracy based on percentage of supported sentences
        total_sentences = sum(1 for s in response_sentences if s.strip() and len(s.split()) >= 3)
        if total_sentences == 0:
            return 0.5
            
        accuracy = min(1.0, supported_sentences / total_sentences)
        return accuracy
        
    except Exception as e:
        logger.error(f"Error calculating accuracy: {e}")
        return 0.5  # Default to neutral score on error

def calculate_coverage(response: str, documents: List[Document]) -> float:
    """
    Calculate how well the response covers information in the documents.
    
    Args:
        response: LLM response
        documents: Source documents
        
    Returns:
        Float coverage score (0.0-1.0)
    """
    try:
        # Simple heuristic: Calculate percentage of key document terms that appear in response
        # In production, use semantic analysis
        
        # Extract top terms from documents (excluding stopwords)
        stopwords = {"the", "a", "an", "and", "or", "but", "is", "are", "was", "were", "in", "on", "at", "to", "for"}
        doc_text = " ".join([doc.page_content for doc in documents])
        doc_words = [w.lower() for w in doc_text.split() if w.lower() not in stopwords]
        
        # Count word frequencies
        word_freq = {}
        for word in doc_words:
            if len(word) < 3:
                continue  # Skip very short words
            word_freq[word] = word_freq.get(word, 0) + 1
        
        # Get top words by frequency
        sorted_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
        top_words = [word for word, _ in sorted_words[:50]]  # Top 50 words
        
        # Check coverage of top words in response
        response_lower = response.lower()
        words_covered = sum(1 for word in top_words if word in response_lower)
        
        # Calculate coverage score
        coverage = min(1.0, words_covered / (len(top_words) or 1))
        return coverage
        
    except Exception as e:
        logger.error(f"Error calculating coverage: {e}")
        return 0.5  # Default to neutral score on error

def calculate_completeness(question: str, response: str) -> float:
    """
    Calculate how completely the response addresses the question.
    
    Args:
        question: User question
        response: LLM response
        
    Returns:
        Float completeness score (0.0-1.0)
    """
    try:
        # Simple heuristic for completeness: response length relative to question length
        # In production, use NLU to determine if all aspects of the question are addressed
        
        # Calculate normalized length ratio
        question_length = len(question.split())
        response_length = len(response.split())
        
        # For typical QA, responses should be several times longer than questions
        length_ratio = min(response_length / (question_length * 2), 1.0)
        
        # Check if response directly references the question (indicator of addressing it)
        question_terms = set(question.lower().split()) - {"the", "a", "an", "and", "or", "but", "is", "are", "in", "on", "at"}
        term_coverage = sum(1 for term in question_terms if term in response.lower()) / (len(question_terms) or 1)
        
        # Combine metrics
        completeness = 0.7 * length_ratio + 0.3 * term_coverage
        return completeness
        
    except Exception as e:
        logger.error(f"Error calculating completeness: {e}")
        return 0.5  # Default to neutral score on error 