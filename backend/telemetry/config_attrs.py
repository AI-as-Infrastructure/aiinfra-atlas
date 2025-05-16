"""
Provides unified test target config attribute extraction for telemetry spans.
"""
from typing import Dict, Any
import logging

def get_test_target_attributes() -> Dict[str, Any]:
    """Get test target attributes from the unified TargetConfig system."""
    from backend.targets.base_target import TargetConfig
    
    test_target_attrs = {}
    try:
        # Use the centralized TargetConfig to get all configuration
        target_config = TargetConfig()
        unified_config = target_config.get_full_config()
        
        # Get the proper composite target identifier
        composite_target = target_config.composite_target
        
        # Add the main test target attributes
        test_target_attrs.update({
            # Main identifiers
            "target.id": unified_config["target_id"],
            "target_id": unified_config["target_id"],
            "test_target.composite_target": composite_target,
            # LLM configuration
            "llm_model": unified_config["llm_model"],
            "test_target.llm_provider": unified_config["llm_provider"],
            # Search configuration
            "retrieval.search_type": unified_config["search_type"],
            "retrieval.k": unified_config["search_k"],
            "citation_limit": unified_config["citation_limit"],
            "test_target.search_score_threshold": unified_config["search_score_threshold"],
            # Vector store configuration
            "embedding.model": unified_config["embedding_model"],
            "test_target.algorithm": unified_config["algorithm"],
            "test_target.chunk_size": unified_config["chunk_size"],
            "test_target.chunk_overlap": unified_config["chunk_overlap"],
            "test_target.index_name": unified_config["index_name"],
            "test_target.vector_database": unified_config["vector_database"],
            "test_target.chroma_collection": unified_config["chroma_collection"],
        })
        # Include any additional fields from the unified config
        for key, value in unified_config.items():
            attr_key = f"test_target.{key.lower()}"
            if attr_key not in test_target_attrs and isinstance(value, (str, int, float, bool)):
                test_target_attrs[attr_key] = value
        logging.info(f"Using unified target configuration with composite target: {composite_target}")
    except Exception as e:
        logging.error(f"Failed to get unified test target attributes: {e}")
        # Provide minimal fallback attributes to prevent failures
        import os
        test_target = os.getenv('TEST_TARGET', 'unknown')
        test_target_attrs.update({
            "target.id": test_target,
            "target_id": test_target,
            "test_target.error": str(e)
        })
    return test_target_attrs
