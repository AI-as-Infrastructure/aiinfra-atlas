"""
Embedding model utilities for ATLAS.

This module provides functions for creating and managing embedding models,
with appropriate configuration and telemetry instrumentation.
"""

import os
import logging
from typing import Dict, Any, Optional

from langchain_huggingface import HuggingFaceEmbeddings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_embeddings_model(
    model_name: Optional[str] = None,
    config: Optional[Dict[str, Any]] = None
) -> HuggingFaceEmbeddings:
    """
    Get a configured embedding model for document embeddings.
    
    Args:
        model_name: Optional model name override
        config: Optional configuration dictionary
        
    Returns:
        Configured embedding model instance
    """
    if config is None:
        config = {}
        
    # Use provided model name or get from config or environment
    embedding_model = model_name or config.get("embedding_model") or os.getenv(
        "EMBEDDING_MODEL", "Livingwithmachines/bert_1890_1900"
    )
    
    logger.debug(f"Initializing embedding model: {embedding_model}")
    
    try:
        # Create and return the embedding model
        return HuggingFaceEmbeddings(model_name=embedding_model)
    except Exception as e:
        logger.error(f"Error initializing embedding model {embedding_model}: {e}")
        raise ValueError(f"Failed to initialize embedding model {embedding_model}: {e}") 