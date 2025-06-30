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
        # Use exportable config to match exactly what's shown in the UI test target box
        config = target_config.get_exportable_config()
        
        # === TOP-LEVEL METADATA FOR PHOENIX QUERYABILITY ===
        # These are the primary fields for data analysis and filtering
        
        # Atlas Version - prominently displayed for version analysis
        atlas_version = config.get("ATLAS_VERSION", "1.0.0")
        result["atlas_version"] = atlas_version
        result["ATLAS_VERSION"] = atlas_version  # Also add the original key name
        
        # Composite Target - the full identifier combining config profile + vector database
        composite_target = config.get("composite_target", f"{test_target}_unknown")
        result["composite_target"] = composite_target
        
        # Break down composite target into its two queryable components:
        # Component 1: Test Target (configuration profile like k15_openai4o)
        result["atlas_target_profile"] = test_target
        result["test_target_profile"] = test_target  # Alternative naming
        
        # Component 2: Vector Database (like blert_1000)
        vector_db = config.get("chroma_collection", config.get("vector_database", "unknown"))
        result["atlas_vector_database"] = vector_db
        
        # === DIRECT UI CONFIG MAPPING ===
        # Map all exportable fields exactly as they appear in the UI
        
        # Core identification
        result["target_id"] = config.get("target_id", test_target)
        result["target_version"] = config.get("target_version", "1.0")
        
        # LLM Configuration
        result["llm_provider"] = config.get("llm_provider", "")
        result["llm_model"] = config.get("llm_model", "")
        
        # Vector Store and Embedding
        result["vector_database"] = config.get("vector_database", "")
        result["chroma_collection"] = config.get("chroma_collection", "")
        result["embedding_model"] = config.get("embedding_model", "")
        result["large_retrieval_size"] = config.get("large_retrieval_size", 0)
        result["algorithm"] = config.get("algorithm", "")
        
        # Search Configuration
        result["search_type"] = config.get("search_type", "")
        result["search_k"] = config.get("search_k", 0)
        result["search_score_threshold"] = config.get("search_score_threshold", 0.0)
        
        # Text Processing
        result["chunk_size"] = config.get("chunk_size", "")
        result["chunk_overlap"] = config.get("chunk_overlap", "")
        result["pooling"] = config.get("pooling", "mean")
        
        # Output Configuration
        result["citation_limit"] = config.get("citation_limit", 10)
        
        # System Prompt (truncated for span size limits)
        if "system_prompt" in config and config["system_prompt"]:
            prompt = config["system_prompt"]
            if len(prompt) > 300:
                result["system_prompt"] = prompt[:297] + "..."
            else:
                result["system_prompt"] = prompt
        
        # === BACKWARD COMPATIBILITY ===
        # Keep legacy flat naming for existing queries
        result["test_target.id"] = config.get("target_id", test_target)
    
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
