#!/usr/bin/env python3
"""
Auto-generated ATLAS Retriever for blert_1000 (HNSW)
Generated: 2025-07-11 11:52:50
Manifest creation: 2025-07-11 11:38:26
"""
import os
import logging
import asyncio
from typing import Dict, List, Any, Optional, Tuple
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_core.documents.base import Document
from backend.retrievers.base_retriever import BaseRetriever

# Configure logging
logger = logging.getLogger(__name__)

# Define corpus options directly (removed SelfQuery prefix)
CORPUS_OPTIONS = [
    {"value": "all", "label": "All Collections"},
    {"value": "1901_au", "label": "Australia (1901)"},
    {"value": "1901_nz", "label": "New Zealand (1901)"},
    {"value": "1901_uk", "label": "United Kingdom (1901)"}
]


class HansardRetriever(BaseRetriever):
    """Hansard-specific retriever implementation for ATLAS."""
    def __init__(self, config: Dict[str, Any] = None):
        if config is None:
            config = {}
        
        config["CORPUS_OPTIONS"] = CORPUS_OPTIONS
        super().__init__(config)
        self.index_name = "blert_1000"
        self.chunk_size = int("1000")
        self.chunk_overlap = int("100")
        self.embedding_model = "Livingwithmachines/bert_1890_1900"
        self._supports_corpus_filtering = True

        # Location of the persisted Chroma DB
        self.persist_directory = os.getenv("CHROMA_PERSIST_DIRECTORY", "./create/txt/output/chroma_db")
        
        # Initialize LLM instance (required by retriever_call_model.py)
        self._initialize_llm()
        self._initialize_vector_store()

    def _initialize_llm(self):
        """Initialize the LLM instance required by the system."""
        from backend.modules.llm import create_llm
        self.llm = create_llm()
    
    def _initialize_vector_store(self):
        from backend.modules.vector_store_manager import get_vector_store_manager
        
        # Use the vector store manager for connection pooling
        self.vector_manager = get_vector_store_manager()
        self.vector_store = self.vector_manager.get_vector_store(
            collection_name=self.index_name,
            embedding_model=self.embedding_model,
            persist_directory=self.persist_directory
        )
        self._retriever = self.vector_store.as_retriever(search_type="similarity", search_kwargs={"k": 10})

    def get_retriever(self):
        return self._retriever

    def get_config(self) -> Dict[str, Any]:
        return {
            "index_name": self.index_name,
            "chunk_size": self.chunk_size,
            "chunk_overlap": self.chunk_overlap,
            "embedding_model": self.embedding_model,
            "persist_directory": self.persist_directory,
            "supports_corpus_filtering": self._supports_corpus_filtering,
            "algorithm": "HNSW",
            "search_type": "similarity",
            "search_kwargs": {"k": 10}
        }

    @property
    def supports_corpus_filtering(self) -> bool:
        return self._supports_corpus_filtering

    def get_corpus_options(self) -> List[Dict[str, str]]:
        return CORPUS_OPTIONS

    def similar_search(self, query: str, k: int = 10, corpus_filter: Optional[str] = None) -> List[Dict[str, Any]]:
        from backend.modules.document_pool import cleanup_documents
        
        logger.info(f"similar_search: k={k}, corpus_filter={corpus_filter}")
        filter_dict = None
        if corpus_filter and corpus_filter != "all":
            filter_dict = {"corpus": corpus_filter}
        
        # Use standard similarity search
        docs = self.vector_store.similarity_search(query=query, k=k, filter=filter_dict)
        
        # Convert to result format
        results = [{
            "id": doc.metadata.get("id", "unknown"),
            "content": doc.page_content,
            "date": doc.metadata.get("date", "unknown"),
            "url": doc.metadata.get("url", "unknown"),
            "loc": doc.metadata.get("loc", "unknown"),
            "page": doc.metadata.get("page", "unknown"),
            "corpus": doc.metadata.get("corpus", "unknown")
        } for doc in docs]
        
        # Clean up documents to reduce memory pressure
        cleanup_documents(docs)
        
        return results
    
    # LangChain-compatible async implementation
    async def _get_relevant_documents(self, query: str, config: Optional[Dict] = None, **kwargs) -> List[Document]:
        """Internal implementation method called by invoke/ainvoke"""
        k = kwargs.get("k", 10)
        corpus_filter = None
        
        # Extract corpus filter from config if present
        if config and isinstance(config, dict):
            corpus_filter = config.get("corpus_filter")
        
        filter_dict = None
        if corpus_filter and corpus_filter != "all":
            filter_dict = {"corpus": corpus_filter}
        
        # Use standard similarity search
        return self.vector_store.similarity_search(query=query, k=k, filter=filter_dict)
    
    # Public API methods required by LangChain
    def invoke(self, input: str, config: Optional[Dict] = None, **kwargs) -> List[Document]:
        """Synchronous invoke method required by LangChain."""
        import asyncio
        
        # Check if we're already in an event loop
        try:
            loop = asyncio.get_running_loop()
            # If we're in a running loop, we need to handle this differently
            if loop.is_running():
                # Run synchronously by calling the vector store directly
                k = kwargs.get("k", 10)
                corpus_filter = None
                
                # Extract corpus filter from config if present
                if config and isinstance(config, dict):
                    corpus_filter = config.get("corpus_filter")
                
                filter_dict = None
                if corpus_filter and corpus_filter != "all":
                    filter_dict = {"corpus": corpus_filter}
                
                # Use standard similarity search
                return self.vector_store.similarity_search(query=input, k=k, filter=filter_dict)
        except RuntimeError:
            # No event loop running, safe to use asyncio.run()
            pass
        
        return asyncio.run(self._get_relevant_documents(input, config, **kwargs))
    
    async def ainvoke(self, input: str, config: Optional[Dict] = None, **kwargs) -> List[Document]:
        """Asynchronous invoke method required by LangChain."""
        return await self._get_relevant_documents(input, config, **kwargs)
    
    def format_document_for_citation(self, document: Document, idx: Optional[int] = None) -> Optional[Dict[str, Any]]:
        """Instance method version for compatibility with retriever_call_model.py."""
        return format_document_for_citation(document, idx)

# Compatibility helper for citation formatting (imported by streaming.py)
def format_document_for_citation(document: Document, idx: Optional[int] = None) -> Optional[Dict[str, Any]]:
    """Convert a Document into the citation structure expected by the frontend."""
    if not document:
        return None

    meta = getattr(document, 'metadata', {}) or {}
    text = getattr(document, 'page_content', str(document))

    preview = text[:300] + ("..." if len(text) > 300 else "")
    doc_id = meta.get("id") or (f"doc_{idx + 1}" if idx is not None else "unknown")

    return {
        "id": doc_id,
        "source_id": doc_id,
        "title": meta.get("title", f"Document {doc_id}"),
        "url": meta.get("url", ""),
        "date": meta.get("date", ""),
        "page": meta.get("page", ""),
        "corpus": meta.get("corpus", ""),
        "text": preview,
        "quote": preview,
        "content": text,
        "full_content": text,
        "loc": meta.get("loc", ""),
        "weight": 1.0,
        "has_more": len(text) > 300,
    }

# Required functions for compatibility with retriever_call_model.py
def enhance_document_relevance(documents: List[Document], query: str) -> List[Document]:
    """Enhance document relevance using the centralized reranking module."""
    from backend.modules.document_reranking import enhance_document_relevance as _enhance
    return _enhance(documents, query, create_span=False)

def format_citations(documents: List[Document], **kwargs) -> List[Dict[str, Any]]:
    """Format documents as citations for the frontend."""
    return [format_document_for_citation(doc, i) for i, doc in enumerate(documents)]
