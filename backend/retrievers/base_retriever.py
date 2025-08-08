"""
Base Retriever System for ATLAS

This module contains:
1. The BaseRetriever abstract class that all retrievers must implement
2. Utility functions for retriever implementation and document processing
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
                logger.error(f"Error in document retrieval: {e}", exc_info=True)
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
