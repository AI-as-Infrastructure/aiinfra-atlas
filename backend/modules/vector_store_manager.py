#!/usr/bin/env python3
"""
Vector Store Connection Manager
Manages vector store connections with proper cleanup and pooling
"""

import gc
import logging
import threading
import time
import weakref
from typing import Dict, Any, Optional
from contextlib import contextmanager
from langchain_huggingface import HuggingFaceEmbeddings
try:
    from langchain_chroma import Chroma
except ImportError:
    # Fallback to legacy import for compatibility
    from langchain_community.vectorstores import Chroma

logger = logging.getLogger(__name__)

class VectorStoreManager:
    """Manages vector store connections with pooling and cleanup."""
    
    def __init__(self, max_connections: int = 10, cleanup_interval: int = 300):
        self._connections: Dict[str, Any] = {}
        self._embeddings_cache: Dict[str, HuggingFaceEmbeddings] = {}
        self._last_used: Dict[str, float] = {}
        self._lock = threading.Lock()
        self._max_connections = max_connections
        self._cleanup_interval = cleanup_interval
        self._last_cleanup = time.time()
        
        # Use weak references to allow garbage collection
        self._weak_refs: Dict[str, weakref.ReferenceType] = {}
    
    def get_vector_store(self, 
                        collection_name: str, 
                        embedding_model: str, 
                        persist_directory: str) -> Chroma:
        """Get or create a vector store connection."""
        key = f"{collection_name}:{embedding_model}:{persist_directory}"
        
        with self._lock:
            # Check if we need cleanup
            self._maybe_cleanup()
            
            # Check if connection exists and is still valid
            if key in self._connections:
                store = self._connections[key]
                if store is not None:
                    self._last_used[key] = time.time()
                    return store
                else:
                    # Connection was garbage collected, remove it
                    self._cleanup_connection(key)
            
            # Create new connection
            return self._create_connection(key, collection_name, embedding_model, persist_directory)
    
    def _create_connection(self, key: str, collection_name: str, 
                          embedding_model: str, persist_directory: str) -> Chroma:
        """Create a new vector store connection."""
        try:
            # Get or create embedding model
            embeddings = self._get_embeddings(embedding_model)
            
            # Create vector store
            store = Chroma(
                collection_name=collection_name,
                embedding_function=embeddings,
                persist_directory=persist_directory,
            )
            
            # Store connection
            self._connections[key] = store
            self._last_used[key] = time.time()
            
            # Create weak reference for cleanup tracking
            self._weak_refs[key] = weakref.ref(store, lambda ref: self._cleanup_connection(key))
            
            logger.debug(f"Created vector store connection: {key}")
            return store
            
        except Exception as e:
            logger.error(f"Failed to create vector store connection {key}: {e}")
            raise
    
    def _get_embeddings(self, model_name: str) -> HuggingFaceEmbeddings:
        """Get or create embedding model (cached)."""
        if model_name not in self._embeddings_cache:
            logger.debug(f"Loading embedding model: {model_name}")
            embeddings = HuggingFaceEmbeddings(model_name=model_name)
            self._embeddings_cache[model_name] = embeddings
        return self._embeddings_cache[model_name]
    
    def _cleanup_connection(self, key: str):
        """Clean up a specific connection."""
        if key in self._connections:
            del self._connections[key]
        if key in self._last_used:
            del self._last_used[key]
        if key in self._weak_refs:
            del self._weak_refs[key]
        logger.debug(f"Cleaned up vector store connection: {key}")
    
    def _maybe_cleanup(self):
        """Perform cleanup if needed."""
        current_time = time.time()
        if current_time - self._last_cleanup > self._cleanup_interval:
            self._cleanup_expired_connections()
            self._last_cleanup = current_time
    
    def _cleanup_expired_connections(self):
        """Clean up expired connections."""
        current_time = time.time()
        expired_keys = []
        
        for key, last_used in self._last_used.items():
            if current_time - last_used > self._cleanup_interval:
                expired_keys.append(key)
        
        for key in expired_keys:
            self._cleanup_connection(key)
            logger.debug(f"Cleaned up expired connection: {key}")
    
    def cleanup_all(self):
        """Clean up all connections."""
        with self._lock:
            for key in list(self._connections.keys()):
                self._cleanup_connection(key)
            
            # Clear embedding cache
            self._embeddings_cache.clear()
            
            # Force garbage collection
            gc.collect()
            
            logger.info("Cleaned up all vector store connections")
    
    @contextmanager
    def get_connection(self, collection_name: str, embedding_model: str, persist_directory: str):
        """Context manager for vector store connections."""
        store = self.get_vector_store(collection_name, embedding_model, persist_directory)
        try:
            yield store
        finally:
            # Connection is managed by the pool, no explicit cleanup needed
            pass

# Global instance
_vector_store_manager = VectorStoreManager()

def get_vector_store_manager() -> VectorStoreManager:
    """Get the global vector store manager."""
    return _vector_store_manager