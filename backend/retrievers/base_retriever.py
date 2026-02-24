"""
Base Retriever System for ATLAS

This module contains:
1. The BaseRetriever abstract class that all retrievers must implement
2. Utility functions for retriever implementation and document processing

Directory Structure:
- backend/retrievers/ - Contains base classes and utilities (this directory)
  - base_retriever.py - Base class for all retrievers
  - retriever_config_utils.py - Configuration utilities
  - templates/ - Templates for creating new retrievers

- backend/corpus/ - Contains ALL build artifacts from the corpus wizard
  - {corpus_name}_adapter.py - The corpus adapter (provides retrieval functionality)
  - corpus_active.json - Active corpus configuration
  - chroma_db/ - Vector store data
  - manifest.json - Corpus metadata and statistics
  - bm25_corpus.jsonl - BM25 search data
  - corpus_config.yaml - Detailed corpus configuration

Note: When the corpus wizard builds a corpus, ALL artifacts (including the corpus adapter)
are stored together in backend/corpus/ for consistency and easy management.
The retriever loader checks backend/corpus/ first (for corpus adapters), then
backend/retrievers/ for backward compatibility with manually created retrievers.
The corpus adapter inherits from BaseRetriever and provides corpus-specific
retrieval capabilities.
"""

import os
import re
import uuid
import logging
import datetime
from abc import ABC, abstractmethod
from backend.retrievers.retriever_config_utils import require_config_keys, get_with_default
from typing import Dict, List, Any, Optional, Sequence, Tuple
from typing import TypedDict
import asyncio

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langchain_core.documents.base import Document
from langchain_core.callbacks import CallbackManagerForRetrieverRun
from langchain_core.runnables import RunnableConfig

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import only system_prompts at module level (not config)
from backend.modules.system_prompts import system_prompt, contextualize_q_system_prompt

# Import telemetry
from backend.telemetry import (
    create_span, SpanAttributes, OpenInferenceSpanKind, SpanNames,
    telemetry_initialized, Status, StatusCode
)

# Use telemetry functions directly

class BaseRetriever(ABC):
    """Base class that defines the interface for all ATLAS retrievers."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize the retriever with configuration.
        Args:
            config: Configuration dictionary with all necessary settings
        """
        # Save basic configuration
        self.config = config if config is not None else {}
        self.retriever_id = self.__class__.__name__
        
        # Get embedding model and other configuration
        self.embedding_model = self.config.get("embedding_model", "unknown")
        
        # Use search_type from config - standardization to similarity happens at the 
        # TargetConfig level in get_full_config(), so we don't need to override here
        self.search_type = self.config.get("search_type", "similarity")
        
        # Record original search type if present
        self.original_search_type = self.config.get("original_search_type")
        
        # Get remaining configuration values with defaults
        self.search_kwargs = self.config.get("search_kwargs", {"k": 3})
        self.index_name = self.config.get("index_name", "unknown")
        self.algorithm = self.config.get("algorithm", "unknown")
        self.chunk_size = self.config.get("chunk_size", 1000)
        self.chunk_overlap = self.config.get("chunk_overlap", 0)
    
    @abstractmethod
    def get_retriever(self):
        """Return the actual retriever implementation for this retriever.
        Returns:
            A retriever object that can be used to retrieve documents
        """
        pass

    
    @abstractmethod
    def get_config(self) -> Dict[str, Any]:
        """Return the complete configuration of this retriever.
        
        Returns:
            A dictionary with all configuration values
        """
        pass
    
    @property
    @abstractmethod
    def supports_corpus_filtering(self) -> bool:
        """Whether this retriever supports filtering by corpus.
        
        Returns:
            True if corpus filtering is supported, False otherwise
        """
        pass
    
    @abstractmethod
    def get_corpus_options(self) -> List[Dict[str, str]]:
        """Get available corpus options for filtering.
        
        Returns:
            A list of dictionaries with 'value' and 'label' keys
        """
        pass
    
    def get_filter_capabilities(self) -> Dict[str, Any]:
        """Get all available filter capabilities for this retriever.
        
        This method provides a unified interface for discovering what filters
        are available. Retrievers can override this to provide additional
        filter types beyond corpus filtering.
        
        Returns:
            A dictionary containing filter capabilities:
            {
                "corpus_filtering": {
                    "supported": bool,
                    "options": List[Dict[str, str]]
                },
                "time_period_filtering": {
                    "supported": bool,
                    "options": List[Dict[str, str]]
                },
                "direction_filtering": {
                    "supported": bool,
                    "options": List[Dict[str, str]]
                }
            }
        """
        # Default implementation provides only corpus filtering
        return {
            "corpus_filtering": {
                "supported": self.supports_corpus_filtering,
                "options": self.get_corpus_options() if self.supports_corpus_filtering else []
            },
            "time_period_filtering": {
                "supported": False,
                "options": []
            },
            "direction_filtering": {
                "supported": False,
                "options": []
            }
        }
    
    @staticmethod
    def get_available_retrievers() -> List[str]:
        """Get a list of all available retriever implementations.
        
        Returns:
            A list of retriever class names available in the retrievers directory
        """
        retrievers_dir = os.path.dirname(os.path.abspath(__file__))
        retrievers = []
        
        # Find all Python files in the retrievers directory
        for filename in os.listdir(retrievers_dir):
            if filename.endswith('.py') and filename not in ['__init__.py', 'base_retriever.py']:
                retriever_name = filename[:-3]  # Remove '.py' extension
                retrievers.append(retriever_name)
        
        return retrievers

    async def aget_relevant_documents(
        self,
        query: str,
        **kwargs: Any,
    ) -> List[Document]:
        """
        Asynchronous method to get relevant documents with telemetry.
        """
        # Create a unique ID for this query if not provided
        qa_id = kwargs.get("qa_id") or str(uuid.uuid4())
        session_id = kwargs.get("session_id")
        
        logger.debug(f"Retrieving documents with qa_id={qa_id}")
        
        # Create a telemetry span for this query if telemetry is initialized
        if telemetry_initialized():
            # Create span attributes for document retrieval
            span_attributes = {
                SpanAttributes.SESSION_ID: session_id,
                SpanAttributes.QA_ID: qa_id,
                "input": query,
                "query": query,
                "retriever.type": self.__class__.__name__,
                "chunking.enabled": self.chunking_enabled if hasattr(self, "chunking_enabled") else False,
                "chunking.size": self.chunk_size,
                "chunking.overlap": self.chunk_overlap,
                "openinference.span.kind": OpenInferenceSpanKind.RETRIEVER
            }
            
            # Span for document retrieval
            with create_span(
                SpanNames.DOCUMENT_RETRIEVAL,
                attributes=span_attributes,
                session_id=session_id
            ) as span:
                try:
                    # Perform the actual retrieval
                    docs = await self._get_relevant_documents(
                        query,
                        **kwargs
                    )
                    
                    # Record information about the results
                    span.set_attribute("document_count", len(docs))
                    span.set_attribute(SpanAttributes.DOCUMENT_COUNT, len(docs))
                    
                    # Get size details for each document (up to 10 docs to avoid giant spans)
                    for i, doc in enumerate(docs[:10]):
                        page_content = getattr(doc, "page_content", "")
                        span.set_attribute(f"document.{i}.content_length", len(page_content) if page_content else 0)
                        
                        # For string metadata fields, get their lengths
                        if hasattr(doc, "metadata") and isinstance(doc.metadata, dict):
                            for key, value in doc.metadata.items():
                                if isinstance(value, str):
                                    span.set_attribute(f"document.{i}.metadata.{key}_length", len(value))
                    
                    # Mark span as successful
                    span.set_status(Status(StatusCode.OK))
                    return docs
                    
                except Exception as e:
                    # Record error in span
                    span.record_exception(e)
                    span.set_status(Status(StatusCode.ERROR, str(e)))
                    raise
        else:
            # If telemetry is not initialized, just do the retrieval directly
            try:
                docs = await self._get_relevant_documents(query, **kwargs)
                return docs
            except Exception as e:
                logger.error(f"Error in document retrieval: {e}")
                raise

    @abstractmethod
    async def _get_relevant_documents(
        self,
        query: str,
        **kwargs: Any,
    ) -> List[Document]:
        """
        Abstract method to be implemented by specific retrievers.
        """
        pass

    def get_relevant_documents(
        self,
        query: str,
        **kwargs: Any,
    ) -> List[Document]:
        """
        Synchronous method to get relevant documents.
        """
        return asyncio.run(self.aget_relevant_documents(query, **kwargs))


# --- Utility functions for document formatting ---
def format_document_for_citation(document, idx: Optional[int] = None) -> Optional[Dict[str, Any]]:
    """
    Format a document for citation display.

    This utility function converts a document object into a citation format
    suitable for display in the frontend. It extracts key metadata fields
    and truncates content for display purposes.

    Args:
        document: The document to format (typically a LangChain Document)
        idx: Optional index number for the citation

    Returns:
        A dictionary containing citation information, or None if document is invalid
    """
    if not document:
        return None

    # Extract metadata and content from document
    metadata = getattr(document, 'metadata', {})
    content = getattr(document, 'page_content', str(document))

    # Extract key metadata fields with fallbacks
    source = metadata.get('source', 'Unknown')
    # Use chunk_id (vector store document ID) for traceability back to the
    # specific chunk in ChromaDB. Falls back to a generic index-based ID.
    chunk_id = metadata.get('chunk_id', '')
    doc_id = chunk_id or (f"doc_{idx + 1}" if idx is not None else metadata.get('id', 'unknown'))

    # Support both new 2-filter system and legacy corpus field
    filter_1 = metadata.get('filter_1')
    filter_2 = metadata.get('filter_2')
    corpus = metadata.get('corpus')  # Legacy field
    corpus_label = metadata.get('corpus_label')  # Human-readable label

    # Build corpus display string - prefer human-readable label
    corpus_display = corpus_label or corpus  # Prefer label over ID
    if filter_1 and filter_2:
        corpus_display = f"{filter_1}/{filter_2}"
    elif filter_1 and not corpus_label:
        corpus_display = filter_1
    elif not corpus_display:
        corpus_display = 'Unknown'

    # Build title from metadata or source filename
    title = metadata.get('title', '')
    if not title and source:
        title = source.rsplit('/', 1)[-1].rsplit('\\', 1)[-1]

    # 300-char preview for display
    preview = content[:300] if len(content) > 300 else content

    # Extract optional enrichment metadata
    enrichment_fields = {}
    for field in ['day_of_week', 'day', 'month', 'year', 'date', 'title', 'author']:
        if field in metadata:
            enrichment_fields[field] = metadata[field]

    # Build citation dictionary with all fields frontend expects
    citation = {
        # Core identification
        "id": doc_id,
        "retrieval_id": doc_id,
        "source": source,
        "corpus": corpus_display,
        # Display fields (CitationList.vue uses text/quote/full_content)
        "title": title,
        "text": preview,
        "quote": preview,
        "content": content[:500] if len(content) > 500 else content,
        "full_content": content,
        # Metadata fields
        "url": metadata.get('url', '') or metadata.get('source_url', ''),
        "source_url": metadata.get('source_url', '') or metadata.get('url', ''),
        "date": metadata.get('date', ''),
        "page": metadata.get('page', ''),
        "loc": metadata.get('loc', ''),
        # Scoring
        "weight": 1.0,
        "has_more": len(content) > 300,
        # Raw metadata for additional access
        "metadata": metadata,
    }

    # Add enrichment fields if present
    if enrichment_fields:
        citation["enrichment"] = enrichment_fields

    # Add index if provided
    if idx is not None:
        citation["idx"] = idx

    return citation


# --- State schema for retriever operations ---
class State(TypedDict):
    input: str
    chat_history: Sequence[BaseMessage]
    context: str
    answer: str
    question: str
    session_id: str
    qa_id: str
    request_structured_citations: Optional[bool]
