"""
retriever_config_utils.py

Utility functions for retriever configuration validation and defaults in ATLAS.
"""
from typing import Dict, List, Any

class ConfigError(Exception):
    """Custom exception for configuration errors."""
    pass

def require_config_keys(config: Dict[str, Any], required_keys: List[str]) -> Dict[str, Any]:
    """
    Ensure all required keys are present in the config. Raises ConfigError if any are missing.
    Returns a dict of just the required keys/values for convenience.
    """
    missing = [k for k in required_keys if k not in config]
    if missing:
        raise ConfigError(f"Missing required config keys: {missing}")
    return {k: config[k] for k in required_keys}

def get_with_default(config: Dict[str, Any], key: str, default: Any) -> Any:
    """
    Return config[key] if present, otherwise return default.
    """
    return config.get(key, default)
