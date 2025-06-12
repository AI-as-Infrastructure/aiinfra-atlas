"""
Telemetry configuration attribute helpers.

This module provides functions for gathering test target configuration
attributes in a format compatible with OpenTelemetry.
"""

import os
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

def get_test_target_attributes() -> Dict[str, Any]:
    """
    Get test target attributes in a flat format for OpenTelemetry spans.
    
    Returns:
        Dict[str, Any]: Dictionary of test target attributes with flattened keys
    """
    result = {}
    
    # Get current test target from environment
    test_target = os.getenv('TEST_TARGET', 'unknown')
    result["test_target"] = test_target
    
    try:
        # Import the base target for unified config
        from backend.targets.base_target import TargetConfig
        target_config = TargetConfig()
        config = target_config.get_full_config()
        
        # Add all the required UI attributes with exact keys expected by Phoenix
        result["test_target.id"] = config.get("target_id", "")
        result["embedding_model"] = config.get("embedding_model", "")
        result["search_type"] = config.get("search_type", "")
        result["search_k"] = config.get("search_k", 0)
        result["search_score_threshold"] = config.get("search_score_threshold", 0)
        result["pooling"] = config.get("pooling", "mean")
        result["large_retrieval_size"] = config.get("large_retrieval_size", 0)
        result["algorithm"] = config.get("algorithm", "")
        result["chunk_size"] = config.get("chunk_size", "")
        result["chunk_overlap"] = config.get("chunk_overlap", "")
        result["llm_provider"] = config.get("llm_provider", "")
        result["llm_model"] = config.get("llm_model", "")
        result["composite_target"] = config.get("composite_target", "")
        result["atlas_version"] = config.get("ATLAS_VERSION", "0.1.0")
        
        # Add system prompt
        if "system_prompt" in config:
            result["system_prompt"] = config.get("system_prompt", "")[:300] + "..."  # Truncate for size
        
        # Add environment-specific configurations
        result["multi_corpus_vectorstore"] = os.getenv("MULTI_CORPUS_VECTORSTORE", "False")
        result["chroma_collection_name"] = os.getenv("CHROMA_COLLECTION_NAME", "")
        
        # Add any other attributes present in the config
        for key, value in config.items():
            if isinstance(value, (str, int, float, bool)) and key not in result:
                result[key.lower()] = value
    
    except Exception as e:
        logger.warning(f"Failed to get test target attributes from TargetConfig: {e}")
        try:
            # Fallback to module import
            import importlib
            target_module = importlib.import_module(f"backend.targets.{test_target}")
            
            # Add basic attributes
            if hasattr(target_module, 'TARGET_ID'):
                result["test_target.id"] = target_module.TARGET_ID
            
            if hasattr(target_module, 'MODEL'):
                result["llm_model"] = target_module.MODEL
            
            if hasattr(target_module, 'EMBEDDING_MODEL'):
                result["embedding_model"] = target_module.EMBEDDING_MODEL
            
            if hasattr(target_module, 'SEARCH_TYPE'):
                result["search_type"] = target_module.SEARCH_TYPE
            
            if hasattr(target_module, 'SEARCH_K'):
                result["search_k"] = target_module.SEARCH_K
            
            if hasattr(target_module, 'CITATION_LIMIT'):
                result["citation_limit"] = target_module.CITATION_LIMIT
            
        except Exception as e:
            logger.warning(f"Failed to get test target attributes from module: {e}")
    
    return result
