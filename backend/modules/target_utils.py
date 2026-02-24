"""
Shared utilities for test target configuration management.

This module provides functions for generating and validating test target
configurations, reducing code duplication across the application.
"""

from datetime import datetime
from typing import Dict, Any, List, Tuple
import logging

logger = logging.getLogger(__name__)

# Default values for target configuration
TARGET_DEFAULTS = {
    'llm_provider': 'anthropic',
    'llm_model': 'claude-sonnet-4-20250514',
    'search_type': 'similarity',
    'search_k': 20,
    'search_score_threshold': 0.7,
    'citation_limit': 10,
    'large_retrieval_size_single': 120,
    'large_retrieval_size_all': 120,
    'algorithm': 'ensemble',
    'temperature': 0.7,
    'max_tokens': 4096,
    'pooling': 'mean',
    'chunk_size': 1000,
    'chunk_overlap': 200,
    'vector_database': 'chromadb',
}


def build_target_config_content(
    target_config: Dict[str, Any],
    action: str = "created",
    source: str = "ConfigManager",
    corpus_name: str = None,
    include_extended: bool = False
) -> str:
    """
    Generate target configuration file content from a config dictionary.

    Args:
        target_config: Dictionary containing target configuration values
        action: Action description for the header comment (e.g., "created", "updated")
        source: Source of the configuration (e.g., "ConfigManager", "Corpus Wizard")
        corpus_name: Optional corpus name to include in header
        include_extended: Include extended fields (chunk_size, chunk_overlap, vector_database)

    Returns:
        String content for the target .txt file
    """
    lines = [
        f"# Target configuration {action} by {source}",
        f"# {action.capitalize()}: {datetime.now().isoformat()}",
    ]

    if corpus_name:
        lines.append(f"# Corpus: {corpus_name}")

    lines.append("")

    # Core LLM configuration
    lines.append(f"LLM_PROVIDER={target_config.get('llm_provider', TARGET_DEFAULTS['llm_provider'])}")
    lines.append(f"LLM_MODEL={target_config.get('llm_model', TARGET_DEFAULTS['llm_model'])}")

    # Search configuration
    lines.append(f"SEARCH_TYPE={target_config.get('search_type', TARGET_DEFAULTS['search_type'])}")
    lines.append(f"SEARCH_K={target_config.get('search_k', TARGET_DEFAULTS['search_k'])}")
    # Handle both 'search_score_threshold' and 'score_threshold' keys
    score_threshold = target_config.get('search_score_threshold') or target_config.get('score_threshold', TARGET_DEFAULTS['search_score_threshold'])
    lines.append(f"SEARCH_SCORE_THRESHOLD={score_threshold}")
    lines.append(f"CITATION_LIMIT={target_config.get('citation_limit', TARGET_DEFAULTS['citation_limit'])}")

    # Retrieval size configuration
    # Handle both naming conventions
    large_single = target_config.get('large_retrieval_size_single') or target_config.get('large_retrieval_size_single_corpus', TARGET_DEFAULTS['large_retrieval_size_single'])
    large_all = target_config.get('large_retrieval_size_all') or target_config.get('large_retrieval_size_all_corpus', TARGET_DEFAULTS['large_retrieval_size_all'])
    lines.append(f"LARGE_RETRIEVAL_SIZE_SINGLE_CORPUS={large_single}")
    lines.append(f"LARGE_RETRIEVAL_SIZE_ALL_CORPUS={large_all}")

    # Algorithm configuration
    lines.append(f"ALGORITHM={target_config.get('algorithm', TARGET_DEFAULTS['algorithm'])}")

    # Extended fields (for corpus wizard builds)
    if include_extended:
        lines.append(f"CHUNK_SIZE={target_config.get('chunk_size', TARGET_DEFAULTS['chunk_size'])}")
        lines.append(f"CHUNK_OVERLAP={target_config.get('chunk_overlap', TARGET_DEFAULTS['chunk_overlap'])}")
        lines.append(f"VECTOR_DATABASE={target_config.get('vector_database', TARGET_DEFAULTS['vector_database'])}")

    # Pooling and model parameters
    lines.append(f"POOLING={target_config.get('pooling', TARGET_DEFAULTS['pooling'])}")
    lines.append(f"TEMPERATURE={target_config.get('temperature', TARGET_DEFAULTS['temperature'])}")
    lines.append(f"MAX_TOKENS={target_config.get('max_tokens', TARGET_DEFAULTS['max_tokens'])}")

    # Version tracking
    lines.append("TARGET_VERSION=1.0")

    return '\n'.join(lines)


def generate_target_id(target_config: Dict[str, Any]) -> str:
    """
    Generate a target ID from configuration.

    Args:
        target_config: Target configuration dictionary

    Returns:
        Generated target ID string (e.g., "k20_claude4")
    """
    search_k = target_config.get('search_k', TARGET_DEFAULTS['search_k'])
    llm_model = target_config.get('llm_model', TARGET_DEFAULTS['llm_model'])

    # Normalize model name for ID
    model_short = llm_model.replace('-', '_').replace('.', '_')

    # Truncate if too long
    if len(model_short) > 20:
        model_short = model_short[:20]

    return f"k{search_k}_{model_short}"


def parse_target_file(content: str) -> Dict[str, Any]:
    """
    Parse a target configuration file into a dictionary.

    Args:
        content: File content as string

    Returns:
        Dictionary of configuration values
    """
    config = {}

    for line in content.splitlines():
        line = line.strip()
        if line and not line.startswith('#') and '=' in line:
            key, value = line.split('=', 1)
            # Strip quotes if present
            value = value.strip().strip('"').strip("'")
            config[key.strip()] = value

    return config


def validate_target_config(target_config: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """
    Validate a target configuration dictionary.

    Args:
        target_config: Configuration to validate

    Returns:
        Tuple of (is_valid, list of error messages)
    """
    errors = []

    # Required fields
    required_fields = ['llm_provider', 'llm_model']
    for field in required_fields:
        if not target_config.get(field):
            errors.append(f"Missing required field: {field}")

    # Validate LLM provider
    valid_providers = ['anthropic', 'openai', 'google', 'bedrock', 'ollama']
    provider = target_config.get('llm_provider', '')
    if provider and provider not in valid_providers:
        errors.append(f"Invalid LLM provider: {provider}. Must be one of: {', '.join(valid_providers)}")

    # Validate numeric ranges
    search_k = target_config.get('search_k')
    if search_k is not None:
        try:
            k = int(search_k)
            if k < 1 or k > 100:
                errors.append("search_k must be between 1 and 100")
        except (TypeError, ValueError):
            errors.append("search_k must be a valid integer")

    temperature = target_config.get('temperature')
    if temperature is not None:
        try:
            t = float(temperature)
            if t < 0 or t > 2:
                errors.append("temperature must be between 0 and 2")
        except (TypeError, ValueError):
            errors.append("temperature must be a valid number")

    max_tokens = target_config.get('max_tokens')
    if max_tokens is not None:
        try:
            m = int(max_tokens)
            if m < 1 or m > 100000:
                errors.append("max_tokens must be between 1 and 100000")
        except (TypeError, ValueError):
            errors.append("max_tokens must be a valid integer")

    return len(errors) == 0, errors


def map_config_to_frontend(config: Dict[str, str]) -> Dict[str, Any]:
    """
    Map backend target config keys to frontend expectations.

    Args:
        config: Backend configuration dictionary

    Returns:
        Dictionary with frontend-compatible keys
    """
    return {
        "llm_provider": config.get("LLM_PROVIDER", ""),
        "llm_model": config.get("LLM_MODEL", ""),
        "search_type": config.get("SEARCH_TYPE", "similarity"),
        "search_k": int(config.get("SEARCH_K", 20)),
        "search_score_threshold": float(config.get("SEARCH_SCORE_THRESHOLD", 0.7)),
        "citation_limit": int(config.get("CITATION_LIMIT", 10)),
        "large_retrieval_size_single": int(config.get("LARGE_RETRIEVAL_SIZE_SINGLE_CORPUS", 120)),
        "large_retrieval_size_all": int(config.get("LARGE_RETRIEVAL_SIZE_ALL_CORPUS", 120)),
        "algorithm": config.get("ALGORITHM", "ensemble"),
        "temperature": float(config.get("TEMPERATURE", 0.7)),
        "max_tokens": int(config.get("MAX_TOKENS", 4096)),
        "pooling": config.get("POOLING", "mean"),
    }
