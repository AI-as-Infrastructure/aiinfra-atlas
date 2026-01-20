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
# Avoid importing Document here to keep this module lightweight; use Any in type hints.
from backend.retrievers.base_retriever import BaseRetriever
import time

# Configure logging
logger = logging.getLogger(__name__)


class HansardRetriever(BaseRetriever):
    """Hansard retriever with optional hybrid search (dense + BM25 via RRF)."""
    def __init__(self, config: Dict[str, Any] | None = None):
        if config is None:
            config = {}

        # Load corpus options dynamically from manifest
        from backend.modules.manifest_loader import get_corpus_options, get_corpus_values
        config["CORPUS_OPTIONS"] = get_corpus_options()

        # Store corpus IDs for balanced search operations
        self._corpus_ids = get_corpus_values()

        # Base initialization
        super().__init__(config)

        # Basic settings (align to collection env/config)
        self.index_name = os.getenv("CHROMA_COLLECTION_NAME", "blert_1000")
        # self.chunk_size, self.chunk_overlap, and self.embedding_model are set by BaseRetriever from config
        self._supports_corpus_filtering = True

        # Persisted Chroma DB
        self.persist_directory = os.getenv("CHROMA_PERSIST_DIRECTORY", "backend/targets/chroma_db")

        # Initialize LLM and vector store
        self._initialize_llm()
        self._initialize_vector_store()

        # Retrieval sizing — accept values from retriever_config/env
        try:
            self.search_k_param = int(self.config.get("search_k", 10))
        except Exception:
            self.search_k_param = 10
        try:
            self.large_single = int(
                self.config.get(
                    "LARGE_RETRIEVAL_SIZE_SINGLE_CORPUS",
                    int(os.getenv("LARGE_RETRIEVAL_SIZE_SINGLE_CORPUS", "120"))
                )
            )
        except Exception:
            self.large_single = 120
        try:
            self.large_all = int(
                self.config.get(
                    "LARGE_RETRIEVAL_SIZE_ALL_CORPUS",
                    int(os.getenv("LARGE_RETRIEVAL_SIZE_ALL_CORPUS", "80"))
                )
            )
        except Exception:
            self.large_all = 80

        # Hybrid search config
        self.default_search_type = os.getenv("HANSARD_SEARCH_TYPE", "hybrid")
        self._bm25_ready = False
        self._bm25 = None
        self._bm25_docs = []  # list of JSONL records: {id, text, metadata}
        self._bm25_docid_to_idx = {}
        self._maybe_initialize_bm25()

        # Store last retrieval metrics for telemetry
        self._last_retrieval_metrics = {}

    def get_retrieval_metrics(self) -> Dict[str, Any]:
        """Get metrics from the last retrieval operation for telemetry."""
        return dict(self._last_retrieval_metrics)



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
            "search_type": self.default_search_type,
            "search_kwargs": {"k": 10},
            "bm25_ready": self._bm25_ready,
        }

    @property
    def supports_corpus_filtering(self) -> bool:
        return self._supports_corpus_filtering

    def get_corpus_options(self) -> List[Dict[str, str]]:
        from backend.modules.manifest_loader import get_corpus_options
        return get_corpus_options()

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

    # --------------------------
    # Hybrid search internals
    # --------------------------

    def _maybe_initialize_bm25(self) -> None:
        if self._bm25_ready:
            return
        try:
            try:
                from rank_bm25 import BM25Okapi  # type: ignore
            except Exception:
                logger.warning("rank_bm25 not installed; dense-only mode")
                return

            import json
            import re
            from pathlib import Path

            TOKEN_RE = re.compile(r"\b\w+\b", re.UNICODE)
            # Resolve default corpus path relative to the backend directory to avoid CWD issues
            backend_dir = Path(__file__).resolve().parents[1]
            default_path = backend_dir / "targets" / "bm25_corpus.jsonl"
            bm25_env = os.getenv("BM25_CORPUS")
            corpus_path = Path(bm25_env) if bm25_env else default_path
            if not corpus_path.exists():
                logger.warning(f"BM25 corpus not found: {corpus_path} (dense-only mode)")
                return

            texts = []
            with corpus_path.open("r", encoding="utf-8") as fh:
                for i, line in enumerate(fh):
                    try:
                        rec = json.loads(line)
                    except Exception:
                        continue
                    if not isinstance(rec, dict) or "id" not in rec:
                        continue
                    self._bm25_docs.append(rec)
                    self._bm25_docid_to_idx[rec["id"]] = i
                    tokens = [t.lower() for t in TOKEN_RE.findall(rec.get("text", ""))]
                    texts.append(tokens)

            if not texts:
                logger.warning("BM25 corpus empty; dense-only mode")
                return

            self._bm25 = BM25Okapi(texts)
            self._bm25_ready = True
            logger.info(f"BM25 index loaded with {len(self._bm25_docs)} docs")
        except Exception as e:
            logger.warning(f"BM25 init failed: {e} (dense-only mode)")

    def _dense_search_docs(self, query: str, k: int, filter_dict: Optional[Dict[str, Any]]):
        return self.vector_store.similarity_search(query=query, k=k, filter=filter_dict)

    def _dense_search_ids(self, query: str, k: int, filter_dict: Optional[Dict[str, Any]]):
        docs = self._dense_search_docs(query, k, filter_dict)
        return [(self._unique_id_from_meta(getattr(d, "metadata", {})), float(i)) for i, d in enumerate(docs)]

    @staticmethod
    def _unique_id_from_meta(meta: Dict[str, Any]) -> str:
        return str(meta.get("id") or meta.get("doc_id") or meta.get("source_id") or meta.get("_id") or "unknown")

    def _bm25_search_ids(self, query: str, k: int, filter_dict: Optional[Dict[str, Any]] = None) -> List[Tuple[str, float]]:
        if not self._bm25_ready:
            return []
        import re
        TOKEN_RE = re.compile(r"\b\w+\b", re.UNICODE)
        tokens = [t.lower() for t in TOKEN_RE.findall(query)]
        scores = self._bm25.get_scores(tokens)
        ranked = sorted(enumerate(scores), key=lambda x: x[1], reverse=True)
        
        # Apply corpus filtering before selecting top-k
        out: List[Tuple[str, float]] = []
        rank_pos = 0
        for idx, _score in ranked:
            # Apply corpus filter if present
            if filter_dict and isinstance(filter_dict, dict) and "corpus" in filter_dict:
                doc_meta = self._bm25_docs[idx].get("metadata", {}) or {}
                if doc_meta.get("corpus") != filter_dict["corpus"]:
                    continue  # Skip documents not matching corpus filter
            
            doc_id = self._bm25_docs[idx]["id"]
            out.append((doc_id, float(rank_pos)))
            rank_pos += 1
            
            # Stop once we have k filtered results
            if len(out) >= k:
                break
                
        return out

    def _materialize_docs_by_ids(self, ids: List[str], filter_dict: Optional[Dict[str, Any]]):
        result: List[Any] = []
        for doc_id in ids:
            idx = self._bm25_docid_to_idx.get(doc_id)
            if idx is None:
                continue
            rec = self._bm25_docs[idx]
            text = rec.get("text", "")
            meta = rec.get("metadata", {}) or {}

            # Corpus filtering is now handled upstream in search methods

            # Lazy construct a minimal Document-like dict used downstream
            result.append(type("_Doc", (), {"page_content": text, "metadata": meta})())
        return result

    def _candidate_pool_size(self, corpus_filter: Optional[str]) -> int:
        """Decide how many candidates to fetch per-side for hybrid or vector-only.

        - If a specific corpus is selected: use LARGE_RETRIEVAL_SIZE_SINGLE_CORPUS
        - If 'all' or not specified: use LARGE_RETRIEVAL_SIZE_ALL_CORPUS
        Always floor to 10x the configured search_k to preserve recall.
        """
        is_all = (not corpus_filter) or (corpus_filter == "all")
        base = self.large_all if is_all else self.large_single
        return max(base, int(self.search_k_param) * 10)
    
    def _per_corpus_candidate_size(self, corpus_filter: Optional[str]) -> int:
        """Calculate candidates per corpus for balanced retrieval."""
        if corpus_filter and corpus_filter != "all":
            # Single corpus - use full allocation
            return self._candidate_pool_size(corpus_filter)
        
        # Multi-corpus - divide pool across corpora for balance
        total_pool = self._candidate_pool_size(corpus_filter)
        corpora_count = len(self._corpus_ids)
        return max(total_pool // corpora_count, self.search_k_param * corpora_count)
    
    def _balanced_dense_search_ids(self, query: str, corpus_filter: Optional[str]) -> List[Tuple[str, float]]:
        """Perform corpus-balanced dense search for better representation."""
        if corpus_filter and corpus_filter != "all":
            # Single corpus - use standard search
            per_corpus_k = self._candidate_pool_size(corpus_filter)
            return self._dense_search_ids(query, per_corpus_k, {"corpus": corpus_filter})
        
        # Multi-corpus balanced search
        per_corpus_k = self._per_corpus_candidate_size(corpus_filter)
        all_results = []
        
        for corpus_id in self._corpus_ids:
            corpus_results = self._dense_search_ids(query, per_corpus_k, {"corpus": corpus_id})
            all_results.extend(corpus_results)
        
        # Sort by score and return
        all_results.sort(key=lambda x: x[1])
        return all_results
    
    def _balanced_bm25_search_ids(self, query: str, corpus_filter: Optional[str]) -> List[Tuple[str, float]]:
        """Perform corpus-balanced BM25 search for better representation."""
        if not self._bm25_ready:
            return []
            
        if corpus_filter and corpus_filter != "all":
            # Single corpus - use standard search
            per_corpus_k = self._candidate_pool_size(corpus_filter)
            return self._bm25_search_ids(query, per_corpus_k, {"corpus": corpus_filter})
        
        # Multi-corpus balanced search
        per_corpus_k = self._per_corpus_candidate_size(corpus_filter)
        all_results = []
        
        for corpus_id in self._corpus_ids:
            corpus_results = self._bm25_search_ids(query, per_corpus_k, {"corpus": corpus_id})
            all_results.extend(corpus_results)
        
        return all_results
    
    def _ensure_balanced_final_selection(self, fused_ids: List[str], target_k: int, corpus_filter: Optional[str]) -> List[str]:
        """Apply stratified final selection to ensure balanced corpus representation."""
        if corpus_filter and corpus_filter != "all":
            # Single corpus - no balancing needed
            return fused_ids[:target_k]
        
        if not fused_ids:
            return []
        
        # Group documents by corpus
        corpus_docs = {cid: [] for cid in self._corpus_ids}
        
        for doc_id in fused_ids:
            # Look up corpus from BM25 docs
            idx = self._bm25_docid_to_idx.get(doc_id)
            if idx is not None:
                doc_meta = self._bm25_docs[idx].get("metadata", {}) or {}
                corpus = doc_meta.get("corpus")
                if corpus in corpus_docs:
                    corpus_docs[corpus].append(doc_id)
        
        # Calculate target per corpus (roughly equal distribution)
        corpora_count = len(self._corpus_ids)
        per_corpus_target = max(1, target_k // corpora_count)  # At least 1 per corpus
        remainder = target_k % corpora_count
        
        # Build balanced selection
        balanced_selection = []
        corpus_list = self._corpus_ids
        
        # First pass: take target amount from each corpus
        for corpus in corpus_list:
            available = corpus_docs[corpus][:per_corpus_target]
            balanced_selection.extend(available)
        
        # Second pass: distribute remainder documents
        for i in range(remainder):
            corpus = corpus_list[i]
            # Take next available document if we haven't exhausted this corpus
            if len(corpus_docs[corpus]) > per_corpus_target:
                balanced_selection.append(corpus_docs[corpus][per_corpus_target])
        
        # Third pass: fill any remaining slots if we're still short
        if len(balanced_selection) < target_k:
            remaining_needed = target_k - len(balanced_selection)
            used_ids = set(balanced_selection)
            
            # Take any remaining documents in order until we reach target_k
            for doc_id in fused_ids:
                if len(balanced_selection) >= target_k:
                    break
                if doc_id not in used_ids:
                    balanced_selection.append(doc_id)
        
        return balanced_selection[:target_k]
    
    # LangChain-compatible async implementation
    async def _get_relevant_documents(self, query: str, config: Optional[Dict] = None, **kwargs) -> List[Any]:
        """Internal implementation method called by invoke/ainvoke"""
        # Final top-K is governed by target SEARCH_K; we use a larger candidate pool here
        k = kwargs.get("k", self.search_k_param)
        corpus_filter = None

        # Extract corpus filter from config if present
        if config and isinstance(config, dict):
            corpus_filter = config.get("corpus_filter")

        filter_dict: Optional[Dict[str, Any]] = None
        if corpus_filter and corpus_filter != "all":
            filter_dict = {"corpus": corpus_filter}

        # Decide search type
        search_type = (config or {}).get("search_type") or self.default_search_type

        if search_type == "hybrid" and self._bm25_ready:
            per_side = self._candidate_pool_size(corpus_filter)

            t0 = time.perf_counter()
            dense_ranked = self._dense_search_ids(query, per_side, filter_dict)
            t1 = time.perf_counter()
            bm25_ranked = self._bm25_search_ids(query, per_side, filter_dict)
            t2 = time.perf_counter()

            if not dense_ranked and not bm25_ranked:
                return []

            from backend.modules.hybrid_search import rrf_merge
            r0 = time.perf_counter()
            fused_ids = rrf_merge(dense_ranked, bm25_ranked, k=60, top_k=k*2)  # Get more candidates for balancing
            
            # Apply stratified final selection for balanced corpus representation
            balanced_ids = self._ensure_balanced_final_selection(fused_ids, k, corpus_filter)
            r1 = time.perf_counter()

            # Compute simple overlap stats
            dense_ids = [d for d, _ in dense_ranked]
            bm25_ids = [d for d, _ in bm25_ranked]
            overlap = len(set(dense_ids) & set(bm25_ids))
            unique_dense = len(set(dense_ids) - set(bm25_ids))
            unique_bm25 = len(set(bm25_ids) - set(dense_ids))

            docs = self._materialize_docs_by_ids(balanced_ids, filter_dict)

            # Calculate corpus distribution in final results for telemetry
            final_corpus_distribution = {cid: 0 for cid in self._corpus_ids}
            for doc in docs:
                if hasattr(doc, 'metadata'):
                    corpus = doc.metadata.get("corpus")
                    if corpus in final_corpus_distribution:
                        final_corpus_distribution[corpus] += 1
            
            is_balanced_query = (not corpus_filter) or (corpus_filter == "all")

            # Store meaningful metrics for telemetry consumption
            # Build metrics with dynamic corpus distribution
            self._last_retrieval_metrics = {
                "search_type": "hybrid",
                "bm25_ready": True,
                "per_side_candidates": per_side,
                "stratified_selection_applied": is_balanced_query,
                "dense_candidates": len(dense_ranked),
                "dense_time_ms": int((t1 - t0) * 1000),
                "bm25_candidates": len(bm25_ranked),
                "bm25_time_ms": int((t2 - t1) * 1000),
                "rrf_time_ms": int((r1 - r0) * 1000),
                "rrf_overlap": overlap,
                "rrf_unique_dense": unique_dense,
                "rrf_unique_bm25": unique_bm25,
                "rrf_candidates": len(fused_ids),
                "final_documents": len(docs),
            }
            # Add per-corpus document counts dynamically
            for cid, count in final_corpus_distribution.items():
                self._last_retrieval_metrics[f"final_{cid}_docs"] = count

            # Create child spans for hybrid search components (downstream fork pattern)
            try:
                from backend.telemetry.spans import trace_operation
                
                # Dense search child span
                with trace_operation(
                    "hybrid.dense_search",
                    attributes={
                        "candidates": len(dense_ranked),
                        "time_ms": int((t1 - t0) * 1000),
                        "search_type": "vector"
                    },
                    openinference_kind="RETRIEVER"
                ) as dense_span:
                    pass
                
                # BM25 search child span  
                with trace_operation(
                    "hybrid.bm25_search",
                    attributes={
                        "candidates": len(bm25_ranked),
                        "time_ms": int((t2 - t1) * 1000),
                        "search_type": "lexical"
                    },
                    openinference_kind="RETRIEVER"
                ) as bm25_span:
                    pass
                
                # RRF fusion child span
                with trace_operation(
                    "hybrid.rrf_fusion",
                    attributes={
                        "time_ms": int((r1 - r0) * 1000),
                        "overlap": overlap,
                        "unique_dense": unique_dense,
                        "unique_bm25": unique_bm25,
                        "final_docs": len(docs)
                    },
                    openinference_kind="CHAIN"
                ) as rrf_span:
                    pass
                    
            except Exception:
                pass  # Best effort telemetry

            return docs

        # Fallback: vector only — fetch a larger pool to feed reranker downstream
        pool_k = self._candidate_pool_size(corpus_filter)
        v0 = time.perf_counter()
        docs = self.vector_store.similarity_search(query=query, k=pool_k, filter=filter_dict)
        v1 = time.perf_counter()

        # Store meaningful metrics for telemetry consumption
        self._last_retrieval_metrics = {
            "search_type": "vector",
            "bm25_ready": self._bm25_ready,
            "vector_candidates": pool_k,
            "vector_time_ms": int((v1 - v0) * 1000),
            "final_documents": len(docs)
        }

        return docs
    
    # Public API methods required by LangChain
    def invoke(self, input: str, config: Optional[Dict] = None, **kwargs) -> List[Any]:
        """Synchronous invoke method required by LangChain."""
        # Always use synchronous approach to avoid event loop conflicts
        k = kwargs.get("k", self.search_k_param)
        corpus_filter = None

        # Extract corpus filter from config if present
        if config and isinstance(config, dict):
            corpus_filter = config.get("corpus_filter")

        filter_dict: Optional[Dict[str, Any]] = None
        if corpus_filter and corpus_filter != "all":
            filter_dict = {"corpus": corpus_filter}

        search_type = (config or {}).get("search_type") or self.default_search_type

        if search_type == "hybrid" and self._bm25_ready:
            t0 = time.perf_counter()
            dense_ranked = self._balanced_dense_search_ids(input, corpus_filter)
            t1 = time.perf_counter()
            bm25_ranked = self._balanced_bm25_search_ids(input, corpus_filter)
            t2 = time.perf_counter()
            if not dense_ranked and not bm25_ranked:
                return []
            from backend.modules.hybrid_search import rrf_merge
            r0 = time.perf_counter()
            fused_ids = rrf_merge(dense_ranked, bm25_ranked, k=60, top_k=k*2)  # Get more candidates for balancing
            
            # Apply stratified final selection for balanced corpus representation
            balanced_ids = self._ensure_balanced_final_selection(fused_ids, k, corpus_filter)
            r1 = time.perf_counter()

            dense_ids = [d for d, _ in dense_ranked]
            bm25_ids = [d for d, _ in bm25_ranked]
            overlap = len(set(dense_ids) & set(bm25_ids))
            unique_dense = len(set(dense_ids) - set(bm25_ids))
            unique_bm25 = len(set(bm25_ids) - set(dense_ids))

            docs = self._materialize_docs_by_ids(balanced_ids, filter_dict)
            
            # Calculate per-corpus candidates for telemetry
            per_corpus_k = self._per_corpus_candidate_size(corpus_filter)
            is_balanced = (not corpus_filter) or (corpus_filter == "all")
            
            # Calculate corpus distribution in final results for telemetry
            final_corpus_distribution = {cid: 0 for cid in self._corpus_ids}
            for doc in docs:
                if hasattr(doc, 'metadata'):
                    corpus = doc.metadata.get("corpus")
                    if corpus in final_corpus_distribution:
                        final_corpus_distribution[corpus] += 1

            # Store meaningful metrics for telemetry consumption
            corpora_count = len(self._corpus_ids)
            self._last_retrieval_metrics = {
                "search_type": "hybrid",
                "bm25_ready": True,
                "per_side_candidates": per_corpus_k * (corpora_count if is_balanced else 1),
                "per_corpus_candidates": per_corpus_k,
                "corpus_balanced": is_balanced,
                "stratified_selection_applied": is_balanced,
                "dense_candidates": len(dense_ranked),
                "dense_time_ms": int((t1 - t0) * 1000),
                "bm25_candidates": len(bm25_ranked),
                "bm25_time_ms": int((t2 - t1) * 1000),
                "rrf_time_ms": int((r1 - r0) * 1000),
                "rrf_overlap": overlap,
                "rrf_unique_dense": unique_dense,
                "rrf_unique_bm25": unique_bm25,
                "rrf_candidates": len(fused_ids),
                "final_documents": len(docs),
            }
            # Add per-corpus document counts dynamically
            for cid, count in final_corpus_distribution.items():
                self._last_retrieval_metrics[f"final_{cid}_docs"] = count

            return docs

        # Fallback: vector only — with corpus balancing for unfiltered queries
        v0 = time.perf_counter()
        if (not corpus_filter) or (corpus_filter == "all"):
            # Use balanced search for unfiltered queries
            per_corpus_k = self._per_corpus_candidate_size(corpus_filter)
            all_docs = []
            for corpus_id in self._corpus_ids:
                corpus_docs = self.vector_store.similarity_search(
                    query=input, k=per_corpus_k, filter={"corpus": corpus_id}
                )
                all_docs.extend(corpus_docs)
            
            # Sort by relevance and take top k
            # Note: This is approximate since we can't easily re-score across corpora
            docs = all_docs[:k] if len(all_docs) > k else all_docs
            pool_k = per_corpus_k * len(self._corpus_ids)
        else:
            # Single corpus - use standard search
            pool_k = self._candidate_pool_size(corpus_filter)
            docs = self.vector_store.similarity_search(query=input, k=pool_k, filter=filter_dict)
        
        v1 = time.perf_counter()
        is_balanced = (not corpus_filter) or (corpus_filter == "all")

        # Store meaningful metrics for telemetry consumption
        self._last_retrieval_metrics = {
            "search_type": "vector",
            "bm25_ready": self._bm25_ready,
            "vector_candidates": pool_k,
            "corpus_balanced": is_balanced,
            "vector_time_ms": int((v1 - v0) * 1000),
            "final_documents": len(docs)
        }

        return docs
    
    async def ainvoke(self, input: str, config: Optional[Dict] = None, **kwargs) -> List[Any]:
        """Asynchronous invoke method required by LangChain."""
        return await self._get_relevant_documents(input, config, **kwargs)
    
    def format_document_for_citation(self, document: Any, idx: Optional[int] = None) -> Optional[Dict[str, Any]]:
        """Instance method version for compatibility with retriever_call_model.py."""
        return format_document_for_citation(document, idx)

# Compatibility helper for citation formatting (imported by streaming.py)
def format_document_for_citation(document: Any, idx: Optional[int] = None) -> Optional[Dict[str, Any]]:
    """Convert a Document into the citation structure expected by the frontend."""
    if not document:
        return None

    meta = getattr(document, 'metadata', {}) or {}
    text = getattr(document, 'page_content', str(document))

    preview = text[:300] + ("..." if len(text) > 300 else "")
    doc_id = meta.get("id") or (f"doc_{idx + 1}" if idx is not None else "unknown")

    return {
        "id": doc_id,
        "retrieval_id": doc_id,
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
def enhance_document_relevance(documents: List[Any], query: str) -> List[Any]:
    """Enhance document relevance using the centralized reranking module."""
    from backend.modules.document_reranking import enhance_document_relevance as _enhance
    return _enhance(documents, query, create_span=False)

def format_citations(documents: List[Any], **kwargs) -> List[Dict[str, Any]]:
    """Format documents as citations for the frontend."""
    return [format_document_for_citation(doc, i) for i, doc in enumerate(documents)]
