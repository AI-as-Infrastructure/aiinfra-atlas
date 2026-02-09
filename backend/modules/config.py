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


def _get_dynamic_corpus_options() -> List[CorpusOption]:
    """Load corpus options dynamically from manifest."""
    try:
        from backend.modules.manifest_loader import get_corpus_options
        return get_corpus_options()
    except Exception as e:
        logger.warning(f"Failed to load corpus options from manifest: {e}")
        # Minimal fallback - just "all" option
        return [{"value": "all", "label": "All Collections"}]


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
            "corpus_options": _get_dynamic_corpus_options(),
            "algorithm": "hnsw",
            "chunk_size": 1000,
            "chunk_overlap": 200,
            "pooling": "mean",
            "target_id": "default",
            "target_version": "1.0",
            "request_timeout": 30,
            "connection_timeout": 10
        }
    }

# REMOVED: _load_environment_variables function
# Configuration now comes ONLY from corpus_active.json
# No environment variable fallbacks for corpus configuration

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

    try:
        logger.debug("Initializing retriever with configuration")
        retriever_config = config.get("retriever_config", {})

        # Get retriever_module from config - REQUIRED
        retriever_module = retriever_config.get("retriever_module")

        if not retriever_module:
            logger.warning("No retriever_module in configuration. Run corpus wizard to set up a corpus.")
            _retriever = None
            _retriever_instance = None
            return

        # Load the retriever with the specified module
        _retriever_instance = load_retriever(retriever_name=retriever_module, config=retriever_config)

        if _retriever_instance is None:
            logger.warning(f"Failed to load retriever module: {retriever_module}. System will run without retriever until corpus is configured.")
            _retriever = None
            _retriever_instance = None
            return

        _retriever = _retriever_instance
        logger.debug(f"Retriever initialized successfully: {retriever_module}")

    except Exception as e:
        logger.error(f"Failed to initialize retriever: {e}. System will run without retriever.")
        _retriever = None
        _retriever_instance = None

def _load_corpus_active_config() -> Optional[Dict[str, Any]]:
    """Load active corpus configuration from corpus_active.json."""
    corpus_active_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                     'config', 'corpus_active.json')

    if os.path.exists(corpus_active_path):
        try:
            with open(corpus_active_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Failed to load corpus_active.json: {e}")

    return None

def initialize_config() -> Dict[str, Any]:
    """Initialize configuration from corpus_active.json ONLY. Fails fast if not found."""
    global _config, _retriever, _retriever_instance

    if _config is not None:
        logger.debug("Config already initialized, returning cached instance")
        return _config

    # Start with default configuration
    _config = _get_default_config()

    # Load from corpus_active.json - REQUIRED
    corpus_active = _load_corpus_active_config()

    if not corpus_active:
        error_msg = (
            "No corpus_active.json found at backend/config/corpus_active.json. "
            "Please run the corpus wizard to set up a corpus, or create corpus_active.json manually. "
            "The system no longer supports configuration through environment variables."
        )
        logger.error(error_msg)
        # Don't raise here - let corpus wizard work without a corpus
        logger.warning("Continuing without corpus configuration to allow corpus wizard to run")
        _retriever = None
        _retriever_instance = None
        return _config

    logger.info(f"Loading configuration from corpus_active.json")

    # Load corpus configuration - all fields required
    required_fields = ["retriever_module", "collection_name", "embedding_model", "target"]
    missing_fields = [f for f in required_fields if not corpus_active.get(f)]

    if missing_fields:
        error_msg = f"corpus_active.json is missing required fields: {', '.join(missing_fields)}"
        logger.error(error_msg)
        raise ValueError(error_msg)

    # Override with corpus configuration
    _config["retriever_config"]["retriever_module"] = corpus_active["retriever_module"]
    _config["retriever_config"]["collection_name"] = corpus_active["collection_name"]
    _config["retriever_config"]["chroma_persist_directory"] = corpus_active.get("chroma_persist_directory", "backend/corpus/chroma_db")
    _config["retriever_config"]["embedding_model"] = corpus_active["embedding_model"]
    _config["retriever_config"]["chroma_collection_name"] = corpus_active["collection_name"]  # Add for compatibility

    # Add additional configuration fields from corpus_active.json
    if "chunk_size" in corpus_active:
        _config["retriever_config"]["chunk_size"] = corpus_active["chunk_size"]
    if "chunk_overlap" in corpus_active:
        _config["retriever_config"]["chunk_overlap"] = corpus_active["chunk_overlap"]
    if "text_splitter_type" in corpus_active:
        _config["retriever_config"]["text_splitter_type"] = corpus_active["text_splitter_type"]
    if "pooling" in corpus_active:
        _config["retriever_config"]["pooling"] = corpus_active["pooling"]
    if "algorithm" in corpus_active:
        _config["retriever_config"]["algorithm"] = corpus_active["algorithm"]
    if "batch_size" in corpus_active:
        _config["retriever_config"]["batch_size"] = corpus_active["batch_size"]
    if "large_retrieval_size_single_corpus" in corpus_active:
        _config["retriever_config"]["LARGE_RETRIEVAL_SIZE_SINGLE_CORPUS"] = corpus_active["large_retrieval_size_single_corpus"]
    if "large_retrieval_size_all_corpus" in corpus_active:
        _config["retriever_config"]["LARGE_RETRIEVAL_SIZE_ALL_CORPUS"] = corpus_active["large_retrieval_size_all_corpus"]

    # Load target-specific configuration
    target_id = corpus_active["target"]
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

    logger.debug(f"Configuration initialized with target: {target_id} from corpus_active.json")
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
    retriever_config = config.get("retriever_config", {})
    retriever_type = retriever_config.get("retriever_module", "not_configured")
    return {
        **config,
        "retriever_type": retriever_type,
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