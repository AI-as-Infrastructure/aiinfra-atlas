#!/usr/bin/env python3
"""
Document Object Pool Manager
Manages document objects to reduce memory pressure from frequent allocation/deallocation
"""

import gc
import logging
import threading
import time
import weakref
from typing import Dict, List, Any, Optional, Set
from collections import deque
from langchain_core.documents.base import Document

logger = logging.getLogger(__name__)

class DocumentPool:
    """Object pool for Document instances to reduce GC pressure."""
    
    def __init__(self, max_pool_size: int = 1000, cleanup_interval: int = 60):
        self._pool: deque = deque()
        self._active_docs: Set[Document] = set()
        self._lock = threading.Lock()
        self._max_pool_size = max_pool_size
        self._cleanup_interval = cleanup_interval
        self._last_cleanup = time.time()
        
        # Statistics
        self._created_count = 0
        self._reused_count = 0
        self._pool_hits = 0
        self._pool_misses = 0
    
    def acquire_document(self, page_content: str = "", metadata: Dict[str, Any] = None) -> Document:
        """Acquire a document from the pool or create a new one."""
        if metadata is None:
            metadata = {}
        
        with self._lock:
            # Check if cleanup is needed
            self._maybe_cleanup()
            
            # Try to reuse from pool
            if self._pool:
                doc = self._pool.popleft()
                self._pool_hits += 1
                self._reused_count += 1
                
                # Reset document state
                doc.page_content = page_content
                doc.metadata = metadata.copy()
                
                self._active_docs.add(doc)
                return doc
            
            # Create new document
            self._pool_misses += 1
            self._created_count += 1
            
            doc = Document(page_content=page_content, metadata=metadata)
            self._active_docs.add(doc)
            
            return doc
    
    def release_document(self, doc: Document):
        """Return a document to the pool."""
        if doc is None:
            return
        
        with self._lock:
            # Remove from active set
            self._active_docs.discard(doc)
            
            # Add to pool if not full
            if len(self._pool) < self._max_pool_size:
                # Clear content to prevent memory leaks
                doc.page_content = ""
                doc.metadata = {}
                
                self._pool.append(doc)
            # Otherwise let it be garbage collected
    
    def release_documents(self, docs: List[Document]):
        """Release multiple documents at once."""
        for doc in docs:
            self.release_document(doc)
    
    def _maybe_cleanup(self):
        """Perform cleanup if needed."""
        current_time = time.time()
        if current_time - self._last_cleanup > self._cleanup_interval:
            self._cleanup_pool()
            self._last_cleanup = current_time
    
    def _cleanup_pool(self):
        """Clean up the pool by removing excess documents."""
        # Keep pool size reasonable
        while len(self._pool) > self._max_pool_size // 2:
            self._pool.popleft()
        
        # Force garbage collection
        gc.collect()
        
        logger.debug(f"Document pool cleanup: {len(self._pool)} pooled, {len(self._active_docs)} active")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get pool statistics."""
        with self._lock:
            hit_rate = (self._pool_hits / (self._pool_hits + self._pool_misses)) * 100 if (self._pool_hits + self._pool_misses) > 0 else 0
            
            return {
                "pool_size": len(self._pool),
                "active_docs": len(self._active_docs),
                "created_count": self._created_count,
                "reused_count": self._reused_count,
                "pool_hits": self._pool_hits,
                "pool_misses": self._pool_misses,
                "hit_rate_percent": round(hit_rate, 2),
                "max_pool_size": self._max_pool_size
            }
    
    def clear_pool(self):
        """Clear the entire pool."""
        with self._lock:
            self._pool.clear()
            self._active_docs.clear()
            gc.collect()
            logger.info("Document pool cleared")

class DocumentManager:
    """High-level document management with automatic pooling."""
    
    def __init__(self, pool_size: int = 1000):
        self._pool = DocumentPool(max_pool_size=pool_size)
        self._context_docs: Dict[str, List[Document]] = {}
        self._lock = threading.Lock()
    
    def create_documents(self, contents: List[str], metadatas: List[Dict[str, Any]] = None, 
                        context_id: str = None) -> List[Document]:
        """Create multiple documents with optional context tracking."""
        if metadatas is None:
            metadatas = [{}] * len(contents)
        
        docs = []
        for i, content in enumerate(contents):
            metadata = metadatas[i] if i < len(metadatas) else {}
            doc = self._pool.acquire_document(content, metadata)
            docs.append(doc)
        
        # Track documents by context if provided
        if context_id:
            with self._lock:
                self._context_docs[context_id] = docs
        
        return docs
    
    def release_context(self, context_id: str):
        """Release all documents associated with a context."""
        with self._lock:
            if context_id in self._context_docs:
                docs = self._context_docs.pop(context_id)
                self._pool.release_documents(docs)
                logger.debug(f"Released {len(docs)} documents for context: {context_id}")
    
    def cleanup_documents(self, docs: List[Document]):
        """Clean up a list of documents."""
        # Clear large content to reduce memory pressure
        for doc in docs:
            if hasattr(doc, 'page_content') and len(doc.page_content) > 10000:
                # Keep a small preview for debugging
                doc.page_content = doc.page_content[:100] + "..."
        
        # Release to pool
        self._pool.release_documents(docs)
    
    def get_pool_stats(self) -> Dict[str, Any]:
        """Get pool statistics."""
        return self._pool.get_stats()

# Global instance
_document_manager = DocumentManager()

def get_document_manager() -> DocumentManager:
    """Get the global document manager."""
    return _document_manager

def create_documents_with_pool(contents: List[str], metadatas: List[Dict[str, Any]] = None, 
                              context_id: str = None) -> List[Document]:
    """Convenience function to create documents using the pool."""
    return _document_manager.create_documents(contents, metadatas, context_id)

def cleanup_documents(docs: List[Document]):
    """Convenience function to clean up documents."""
    _document_manager.cleanup_documents(docs)

def release_context_documents(context_id: str):
    """Convenience function to release documents by context."""
    _document_manager.release_context(context_id)