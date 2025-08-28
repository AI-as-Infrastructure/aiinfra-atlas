"""
Enhanced configuration management for ATLAS.

This module provides centralized configuration loading and access with strong typing,
validation, and convenient helper methods. It loads configuration from multiple sources
in a hierarchical manner:

1. Default configuration values
2. Environment variables
3. Target-specific configuration files

Configuration is validated before use to ensure all required values are present.
"""

import os
import json
import logging
import traceback
from typing import Dict, List, Any, Optional, TypedDict, Union, cast

from backend.retrievers import load_retriever
from backend.modules.system_prompts import system_prompt
from backend.targets.base_target import TargetConfig

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Type definitions for better IDE support and documentation
class CorpusOption(TypedDict):
    value: str
    label: str

class RetrieverConfig(TypedDict):
    embedding_model: str
    search_type: str
    search_k: int
    search_score_threshold: float
    citation_limit: int
    LARGE_RETRIEVAL_SIZE_SINGLE_CORPUS: int
    LARGE_RETRIEVAL_SIZE_ALL_CORPUS: int
    chroma_persist_directory: Optional[str]
    chroma_collection_name: Optional[str]
    supports_corpus_filtering: bool
    corpus_options: List[CorpusOption]
    target_id: Optional[str]
    target_version: Optional[str]
    algorithm: Optional[str]
    chunk_size: Optional[int]
    chunk_overlap: Optional[int]
    pooling: Optional[str]
    request_timeout: Optional[int]
    connection_timeout: Optional[int]


class LLMConfig(TypedDict):
    provider: str
    model: str

class AtlasConfig(TypedDict):
    ATLAS_VERSION: str
    system_prompt: str
    retriever_config: RetrieverConfig
    llm_provider: Optional[str]
    llm_model: Optional[str]

# Module-level variables
_config: Optional[Dict[str, Any]] = None
_retriever = None
_retriever_instance = None

def _get_default_config() -> Dict[str, Any]:
    """Get default configuration values."""
    return {
        "ATLAS_VERSION": "1.0.0",
        "retriever_config": {
            "embedding_model": "Livingwithmachines/bert_1890_1900",
            "search_type": "similarity",
            "search_k": 10,
            "search_score_threshold": 0.0,
            "citation_limit": 10,
            "LARGE_RETRIEVAL_SIZE_SINGLE_CORPUS": 500,
            "LARGE_RETRIEVAL_SIZE_ALL_CORPUS": 500,
            "supports_corpus_filtering": True,
            "corpus_options": [
                {"value": "all", "label": "All Collections"},
                {
                    "value": "1901_au", 
                    "label": "Australia (1901)",
                    "url_message": "Australian Parliament URL not available"
                },
                {
                    "value": "1901_nz", 
                    "label": "New Zealand (1901)",
                    "url_message": "New Zealand Parliament URL not available"
                },
                {
                    "value": "1901_uk", 
                    "label": "United Kingdom (1901)",
                    "url_message": "United Kingdom Parliament URL not available"
                }
            ],
            "algorithm": "hnsw",
            "chunk_size": 1000,
            "chunk_overlap": 200,
            "pooling": os.getenv("POOLING", "mean"),
            "target_id": "default",
            "target_version": "1.0",
            "request_timeout": int(os.getenv("RETRIEVER_REQUEST_TIMEOUT", "30")),
            "connection_timeout": int(os.getenv("RETRIEVER_CONNECTION_TIMEOUT", "10"))
        }
    }

def _load_environment_variables(config: Dict[str, Any]) -> None:
    """Load configuration from environment variables."""
    # Enhanced environment variable mapping
    env_mappings = {
        "ATLAS_VERSION": ["ATLAS_VERSION"],
        "CHROMA_PERSIST_DIRECTORY": ["retriever_config", "chroma_persist_directory"],
        "CHROMA_COLLECTION_NAME": ["retriever_config", "chroma_collection_name"],
        "EMBEDDING_MODEL": ["retriever_config", "embedding_model"],
        "LARGE_RETRIEVAL_SIZE_SINGLE_CORPUS": ["retriever_config", "LARGE_RETRIEVAL_SIZE_SINGLE_CORPUS"],
        "LARGE_RETRIEVAL_SIZE_ALL_CORPUS": ["retriever_config", "LARGE_RETRIEVAL_SIZE_ALL_CORPUS"],
        "TEST_TARGET": ["retriever_config", "target_id"],
        "INDEX_NAME": ["retriever_config", "index_name"],
        "POOLING": ["retriever_config", "pooling"]
    }
    
    # Type conversions
    type_conversions = {
        "LARGE_RETRIEVAL_SIZE_SINGLE_CORPUS": int,
        "LARGE_RETRIEVAL_SIZE_ALL_CORPUS": int,
        "SEARCH_K": int,
        "CITATION_LIMIT": int,
        "SEARCH_SCORE_THRESHOLD": float,
        "CHUNK_SIZE": int,
        "CHUNK_OVERLAP": int
    }
    
    for env_var, config_path in env_mappings.items():
        value = os.getenv(env_var)
        if value is not None:
            # Apply type conversion if needed
            if env_var in type_conversions:
                try:
                    value = type_conversions[env_var](value)
                except ValueError:
                    logger.warning(f"Could not convert {env_var}={value} to {type_conversions[env_var].__name__}")
                    continue
            
            # Update the config at the specified path
            current = config
            for i, key in enumerate(config_path):
                if i == len(config_path) - 1:
                    current[key] = value
                else:
                    if key not in current:
                        current[key] = {}
                    current = current[key]

def _load_target_config(config: Dict[str, Any], target_id: str) -> None:
    """Load target-specific configuration."""
    # Path to target config file
    target_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 
                              'targets', f"{target_id}.txt")
    
    if not os.path.isfile(target_file):
        logger.warning(f"Target configuration file not found: {target_file}")
        return
    
    # Enhanced mapping from target config keys to config paths
    target_mappings = {
        "SEARCH_TYPE": ["retriever_config", "search_type"],
        "SEARCH_K": ["retriever_config", "search_k"],
        "SEARCH_SCORE_THRESHOLD": ["retriever_config", "search_score_threshold"],
        "CITATION_LIMIT": ["retriever_config", "citation_limit"],
        "TARGET_VERSION": ["retriever_config", "target_version"],
        "LARGE_RETRIEVAL_SIZE_SINGLE_CORPUS": ["retriever_config", "LARGE_RETRIEVAL_SIZE_SINGLE_CORPUS"],
        "LARGE_RETRIEVAL_SIZE_ALL_CORPUS": ["retriever_config", "LARGE_RETRIEVAL_SIZE_ALL_CORPUS"],
        "LLM_PROVIDER": ["llm_provider"],
        "LLM_MODEL": ["llm_model"],
        "ALGORITHM": ["retriever_config", "algorithm"],
        "CHUNK_SIZE": ["retriever_config", "chunk_size"],
        "CHUNK_OVERLAP": ["retriever_config", "chunk_overlap"],
        "INDEX_NAME": ["retriever_config", "index_name"],
        "POOLING": ["retriever_config", "pooling"]
    }
    
    # Type conversions
    type_conversions = {
        "SEARCH_K": int,
        "CITATION_LIMIT": int,
        "LARGE_RETRIEVAL_SIZE_SINGLE_CORPUS": int,
        "LARGE_RETRIEVAL_SIZE_ALL_CORPUS": int,
        "SEARCH_SCORE_THRESHOLD": float,
        "CHUNK_SIZE": int,
        "CHUNK_OVERLAP": int
    }
    
    try:
        with open(target_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = [x.strip() for x in line.split('=', 1)]
                    value = value.strip('"').strip("'")
                    
                    # Apply type conversion if needed
                    if key in type_conversions:
                        try:
                            value = type_conversions[key](value)
                        except ValueError:
                            logger.warning(f"Could not convert {key}={value} to {type_conversions[key].__name__}")
                            continue
                    
                    # Update the config if this key is mapped
                    if key in target_mappings:
                        config_path = target_mappings[key]
                        current = config
                        for i, path_key in enumerate(config_path):
                            if i == len(config_path) - 1:
                                current[path_key] = value
                            else:
                                if path_key not in current:
                                    current[path_key] = {}
                                current = current[path_key]
        
        logger.debug(f"Loaded target configuration from {target_file}")
    except Exception as e:
        logger.error(f"Error loading target configuration from {target_file}: {e}")

def validate_config_schema(config: Dict[str, Any]) -> List[str]:
    """Validate configuration schema and return list of errors."""
    errors = []
    
    # Check retriever config
    retriever_config = config.get("retriever_config", {})
    if not isinstance(retriever_config, dict):
        errors.append("retriever_config must be a dictionary")
        return errors
    
    # Check required retriever config fields
    required_fields = ["embedding_model", "search_type", "search_k", "citation_limit",
                      "LARGE_RETRIEVAL_SIZE_SINGLE_CORPUS", "LARGE_RETRIEVAL_SIZE_ALL_CORPUS"]
    for field in required_fields:
        if field not in retriever_config:
            errors.append(f"retriever_config missing required field: {field}")
    
    # Validate types
    if "search_k" in retriever_config and not isinstance(retriever_config["search_k"], int):
        errors.append("search_k must be an integer")
    
    if "citation_limit" in retriever_config and not isinstance(retriever_config["citation_limit"], int):
        errors.append("citation_limit must be an integer")
    
    if "LARGE_RETRIEVAL_SIZE_SINGLE_CORPUS" in retriever_config and not isinstance(retriever_config["LARGE_RETRIEVAL_SIZE_SINGLE_CORPUS"], int):
        errors.append("LARGE_RETRIEVAL_SIZE_SINGLE_CORPUS must be an integer")
    
    if "LARGE_RETRIEVAL_SIZE_ALL_CORPUS" in retriever_config and not isinstance(retriever_config["LARGE_RETRIEVAL_SIZE_ALL_CORPUS"], int):
        errors.append("LARGE_RETRIEVAL_SIZE_ALL_CORPUS must be an integer")
    
    if "search_score_threshold" in retriever_config and not isinstance(retriever_config["search_score_threshold"], (int, float)):
        errors.append("search_score_threshold must be a number")
    
    # Validate corpus options
    corpus_options = retriever_config.get("corpus_options", [])
    if not isinstance(corpus_options, list):
        errors.append("corpus_options must be a list")
    else:
        for i, option in enumerate(corpus_options):
            if not isinstance(option, dict):
                errors.append(f"corpus_option at index {i} must be a dictionary")
            elif "value" not in option or "label" not in option:
                errors.append(f"corpus_option at index {i} must have 'value' and 'label' keys")
    
    return errors

def _initialize_retriever(config: Dict[str, Any]) -> None:
    """Initialize the retriever with the configuration."""
    global _retriever, _retriever_instance
    
    # Import here to avoid circular imports
    from backend.retrievers.hansard_retriever import HansardRetriever
    
    try:
        logger.debug("Initializing retriever with configuration")
        _retriever_instance = HansardRetriever(config.get("retriever_config", {}))
        _retriever = _retriever_instance  # Use HansardRetriever directly, not the LangChain wrapper
        logger.debug("Retriever initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize retriever: {e}")
        raise

def initialize_config() -> Dict[str, Any]:
    """Initialize configuration from environment variables and files."""
    global _config, _retriever, _retriever_instance
    
    if _config is not None:
        logger.debug("Config already initialized, returning cached instance")
        return _config

    # Start with default configuration
    _config = _get_default_config()
    
    # Load configuration from environment variables
    _load_environment_variables(_config)
    
    # Load target-specific configuration
    target_id = os.getenv("TEST_TARGET", "default")
    _load_target_config(_config, target_id)
    
    # Store target ID in config for reference
    if "retriever_config" in _config and isinstance(_config["retriever_config"], dict):
        _config["retriever_config"]["target_id"] = target_id
    
    # Validate the configuration
    errors = validate_config_schema(_config)
    if errors:
        error_msg = f"Configuration validation failed: {'; '.join(errors)}"
        logger.error(error_msg)
        raise ValueError(error_msg)
    
    # Initialize retriever with the configuration
    _initialize_retriever(_config)
    
    logger.debug(f"Configuration initialized with target: {target_id}")
    return _config

def get_config() -> Dict[str, Any]:
    """Get the current configuration."""
    global _config
    if _config is None:
        logger.warning("Configuration not initialized, initializing now")
        initialize_config()
    return _config

def get_retriever():
    """Get the current retriever."""
    global _retriever
    if _retriever is None:
        logger.warning("Retriever not initialized, initializing config now")
        initialize_config()
    return _retriever

def get_retriever_instance():
    """Get the current retriever instance."""
    global _retriever_instance
    if _retriever_instance is None:
        logger.warning("Retriever instance not initialized, initializing config now")
        initialize_config()
    return _retriever_instance

def get_full_config() -> Dict[str, Any]:
    """Get configuration including metadata."""
    config = get_config()
    return {
        **config,
        "retriever_type": "hansard_retriever",
        "retriever_instance": get_retriever_instance().__class__.__name__ if get_retriever_instance() else None,
        "initialized": True
    }

# Helper methods for easier access to specific parts of the config

def get_retriever_config() -> RetrieverConfig:
    """Get just the retriever configuration."""
    config = get_config()
    retriever_config = config.get("retriever_config", {})
    return cast(RetrieverConfig, retriever_config)

def get_llm_config() -> LLMConfig:
    """Get LLM-specific configuration."""
    config = get_config()
    return cast(LLMConfig, {
        "provider": config.get("llm_provider"),
        "model": config.get("llm_model")
    })

def get_system_prompt() -> str:
    """Get the system prompt from system_prompts.py - no fallback."""
    return system_prompt

def get_corpus_options() -> List[CorpusOption]:
    """Get available corpus options."""
    retriever_config = get_retriever_config()
    return retriever_config.get("corpus_options", [])

def get_large_retrieval_size() -> int:
    """Get the large retrieval size for single corpus searches."""
    config = get_config()
    return config["retriever_config"]["LARGE_RETRIEVAL_SIZE_SINGLE_CORPUS"]

def get_large_retrieval_size_all_corpus() -> int:
    """Get the large retrieval size for all corpus searches."""
    config = get_config()
    return config["retriever_config"]["LARGE_RETRIEVAL_SIZE_ALL_CORPUS"]

def get_citation_limit() -> int:
    """Get the citation limit parameter."""
    retriever_config = get_retriever_config()
    return retriever_config.get("citation_limit", 10)

def get_search_type() -> str:
    """Get the search type parameter."""
    retriever_config = get_retriever_config()
    return retriever_config.get("search_type", "similarity")

def get_search_k() -> int:
    """Get the search k parameter."""
    retriever_config = get_retriever_config()
    return retriever_config.get("search_k", 10)

def get_search_score_threshold() -> float:
    """Get the search score threshold parameter."""
    retriever_config = get_retriever_config()
    return retriever_config.get("search_score_threshold", 0.0)

def get_request_timeout() -> int:
    """Get the request timeout parameter in seconds."""
    retriever_config = get_retriever_config()
    return retriever_config.get("request_timeout", 30)

def get_connection_timeout() -> int:
    """Get the connection timeout parameter in seconds."""
    retriever_config = get_retriever_config()
    return retriever_config.get("connection_timeout", 10)

def get_pooling() -> str:
    """Get the pooling parameter."""
    retriever_config = get_retriever_config()
    return retriever_config.get("pooling", "mean") 