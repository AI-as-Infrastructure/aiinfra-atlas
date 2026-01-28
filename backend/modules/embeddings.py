"""
Embedding model utilities for ATLAS.

This module provides functions for creating and managing embedding models,
with appropriate configuration and telemetry instrumentation.
"""

import os
import logging
from typing import Dict, Any, Optional
import torch

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

    # Detect and configure device
    device = "cuda" if torch.cuda.is_available() else "cpu"

    if device == "cuda":
        logger.info(f"🚀 GPU available - will attempt GPU acceleration")
        logger.info(f"   GPU: {torch.cuda.get_device_name(0)}")
    else:
        logger.info(f"💻 No GPU available - will use CPU")

    logger.debug(f"Initializing embedding model: {embedding_model} on {device}")

    try:
        # Create embedding model with explicit device configuration
        # HuggingFaceEmbeddings uses 'model_kwargs' to pass device settings
        model_kwargs = {'device': device}

        # Note: Removed torch.float16 as it causes CUDA kernel errors on some GPUs
        # Float32 (default) works more reliably across different GPU architectures

        embeddings = HuggingFaceEmbeddings(
            model_name=embedding_model,
            model_kwargs=model_kwargs
        )

        # Test the embeddings work on the selected device
        try:
            _ = embeddings.embed_query("test")
            logger.info(f"✅ Embeddings test successful on {device.upper()}")
            return embeddings
        except RuntimeError as test_error:
            if "CUDA" in str(test_error) and device == "cuda":
                logger.warning(f"⚠️  GPU test failed - falling back to CPU")
                logger.info(f"   Error: {str(test_error)[:100]}...")
                logger.info("💻 Reinitializing embeddings in CPU mode")

                # Fall back to CPU
                model_kwargs = {'device': 'cpu'}
                cpu_embeddings = HuggingFaceEmbeddings(
                    model_name=embedding_model,
                    model_kwargs=model_kwargs
                )
                logger.info("✅ CPU fallback successful - embeddings ready")
                return cpu_embeddings
            else:
                raise

    except Exception as e:
        logger.error(f"Error initializing embedding model {embedding_model}: {e}")
        raise ValueError(f"Failed to initialize embedding model {embedding_model}: {e}") 