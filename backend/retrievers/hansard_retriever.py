#!/usr/bin/env python3
"""
Auto-generated ATLAS Retriever for blert_1000 (HNSW)
Generated: 2025-06-12 21:18:33
Manifest creation: 2025-06-12 21:16:11
"""
import os
import logging
import asyncio
from typing import Dict, List, Any, Optional, Tuple
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_core.documents.base import Document
from backend.retrievers.base_retriever import BaseRetriever

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
        self.chunk_size = "1000"
        self.chunk_overlap = "100"
        self.embedding_model = "Livingwithmachines/bert_1890_1900"
        self._supports_corpus_filtering = True
        
        # Store reranking metrics for later retrieval
        self.reranking_metrics = []

        # Location of the persisted Chroma DB
        self.persist_directory = os.getenv("CHROMA_PERSIST_DIRECTORY", "./create/txt/output/chroma_db")
        self._initialize_vector_store()

    def _initialize_vector_store(self):
        self.embeddings = HuggingFaceEmbeddings(model_name=self.embedding_model)
        self.vector_store = Chroma(
            collection_name=self.index_name,
            embedding_function=self.embeddings,
            persist_directory=self.persist_directory,
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
        }

    @property
    def supports_corpus_filtering(self) -> bool:
        return self._supports_corpus_filtering

    def get_corpus_options(self) -> List[Dict[str, str]]:
        return CORPUS_OPTIONS
    
    def get_reranking_metrics(self) -> List[Dict[str, Any]]:
        """Get collected reranking metrics and clear the list"""
        metrics = self.reranking_metrics.copy()
        self.reranking_metrics.clear()  # Clear for next query
        return metrics

    def similar_search(self, query: str, k: int = 10, corpus_filter: Optional[str] = None) -> List[Dict[str, Any]]:
        filter_dict = None
        if corpus_filter and corpus_filter != "all":
            filter_dict = {"corpus": corpus_filter}
        
        # Use standard similarity search
        docs = self.vector_store.similarity_search(query=query, k=k, filter=filter_dict)
        return [{
            "id": doc.metadata.get("id", "unknown"),
            "content": doc.page_content,
            "date": doc.metadata.get("date", "unknown"),
            "url": doc.metadata.get("url", "unknown"),
            "loc": doc.metadata.get("loc", "unknown"),
            "page": doc.metadata.get("page", "unknown"),
            "corpus": doc.metadata.get("corpus", "unknown")
        } for doc in docs]
    
    # LangChain-compatible async implementation
    async def _get_relevant_documents(self, query: str, config: Optional[Dict] = None, **kwargs) -> List[Document]:
        """Internal implementation method called by invoke/ainvoke"""
        k = kwargs.get("k", 10)
        corpus_filter = None
        session_id = None
        qa_id = None
        
        # Extract corpus filter and telemetry context from config if present
        if config and isinstance(config, dict):
            corpus_filter = config.get("corpus_filter")
            session_id = config.get("session_id")
            qa_id = config.get("qa_id")
        
        # Handle corpus-specific retrieval logic
        return self._handle_corpus_retrieval(query, corpus_filter, k, session_id, qa_id)
    
    def _handle_corpus_retrieval(self, query: str, corpus_filter: Optional[str], k: int, session_id: Optional[str] = None, qa_id: Optional[str] = None) -> List[Document]:
        """Handle all corpus-specific retrieval logic internally"""
        import logging
        logger = logging.getLogger(__name__)
        
        if corpus_filter and corpus_filter.lower() != "all":
            # Single corpus: retrieve large set then rerank for best quality
            return self._single_corpus_retrieval(query, corpus_filter, k, logger, session_id, qa_id)
        else:
            # All corpora: per-corpus balanced retrieval
            return self._multi_corpus_balanced_retrieval(query, k, logger, session_id, qa_id)
    
    def _single_corpus_retrieval(self, query: str, corpus_filter: str, final_k: int, logger, session_id: Optional[str] = None, qa_id: Optional[str] = None) -> List[Document]:
        """Retrieve from single corpus with reranking"""
        # Get large set for reranking
        large_k = 500  # Could be configurable
        filter_dict = {"corpus": corpus_filter}
        
        # Step 1: Get large set from vector store
        large_documents = self.vector_store.similarity_search(query=query, k=large_k, filter=filter_dict)
        
        # Step 2: Rerank to get best documents  
        reranked_documents = self._rerank_documents(query, large_documents, final_k, session_id, qa_id)
        
        return reranked_documents
    
    def _multi_corpus_balanced_retrieval(self, query: str, final_k: int, logger, session_id: Optional[str] = None, qa_id: Optional[str] = None) -> List[Document]:
        """Retrieve balanced documents from all corpora"""
        # Get available corpora (excluding 'all')
        all_corpora = [option["value"] for option in CORPUS_OPTIONS if option["value"] != "all"]
        
        if not all_corpora:
            # Fallback: standard retrieval without filtering
            return self.vector_store.similarity_search(query=query, k=final_k, filter=None)
        
        # Calculate balanced distribution
        per_corpus_k = 200  # Large retrieval size per corpus (could be configurable)
        docs_per_corpus = max(1, final_k // len(all_corpora))
        remaining_docs = final_k % len(all_corpora)
        
        all_documents = []
        for i, corpus in enumerate(all_corpora):
            # Step 1: Retrieve from this corpus
            filter_dict = {"corpus": corpus}
            corpus_docs = self.vector_store.similarity_search(query=query, k=per_corpus_k, filter=filter_dict)
            
            # Step 2: Determine final count for this corpus
            corpus_final_k = docs_per_corpus
            if i < remaining_docs:  # Distribute remaining docs to first few corpora
                corpus_final_k += 1
            
            # Step 3: Rerank within this corpus
            if corpus_docs:
                reranked_corpus_docs = self._rerank_documents(query, corpus_docs, corpus_final_k, session_id, qa_id)
                all_documents.extend(reranked_corpus_docs)
        return all_documents
    
    def _rerank_documents(self, query: str, documents: List[Document], max_docs: int, session_id: Optional[str] = None, qa_id: Optional[str] = None) -> List[Document]:
        """Rerank documents and add metrics to current span context"""
        try:
            # Add reranking metrics to the current span context instead of creating a new span
            from backend.modules.document_reranking import _rerank_documents_internal
            from opentelemetry import trace
            import time
            import logging
            
            logger = logging.getLogger(__name__)
            start_time = time.time()
            
            # Perform reranking
            reranked_docs, scores = _rerank_documents_internal(documents, query, max_docs)
            
            # Calculate processing time
            processing_time = time.time() - start_time
            
            # Store reranking metrics for later collection by the retrieval span
            rerank_metric = {
                "input_count": len(documents),
                "output_count": len(reranked_docs),
                "processing_time_seconds": processing_time,
                "max_docs": max_docs,
            }
            
            if scores:
                rerank_metric.update({
                    "score_min": min(scores),
                    "score_max": max(scores),
                    "score_avg": sum(scores) / len(scores),
                    "score_range": f"{min(scores):.2f}-{max(scores):.2f}"
                })
            
            # Add to metrics list
            self.reranking_metrics.append(rerank_metric)
            
            return reranked_docs
                
        except ImportError:
            # Fallback: just return the first max_docs (preserving similarity search order)
            logging.warning("Could not import reranking module, using simple truncation")
            return documents[:max_docs]
    
    # Public API methods required by LangChain
    def invoke(self, input: str, config: Optional[Dict] = None, **kwargs) -> List[Document]:
        """Synchronous invoke method required by LangChain."""
        import asyncio
        
        try:
            # Try to get the current event loop
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # We're in an async context, create a task
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(asyncio.run, self._get_relevant_documents(input, config, **kwargs))
                    result = future.result()
            else:
                # No running loop, safe to use asyncio.run
                result = asyncio.run(self._get_relevant_documents(input, config, **kwargs))
        except RuntimeError:
            # Fallback: run in a new event loop
            result = asyncio.new_event_loop().run_until_complete(self._get_relevant_documents(input, config, **kwargs))
        
        return result
    
    async def ainvoke(self, input: str, config: Optional[Dict] = None, **kwargs) -> List[Document]:
        """Asynchronous invoke method required by LangChain."""
        return await self._get_relevant_documents(input, config, **kwargs)

# --- Compatibility helper (used by streaming.py) ---
def format_document_for_citation(document: Document, idx: Optional[int] = None) -> Optional[Dict[str, Any]]:
    """Convert a Document into the citation structure expected by the frontend.

    Args:
        document: LangChain Document instance
        idx: Optional numeric index (for fallback ID generation)

    Returns:
        Dict with citation fields or None if the document is invalid
    """
    if not document:
        return None

    meta = getattr(document, 'metadata', {}) or {}
    text = getattr(document, 'page_content', str(document))

    preview = text[:300] + ("..." if len(text) > 300 else "")
    doc_id = meta.get("id") or (f"doc_{idx}" if idx is not None else "unknown")

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
