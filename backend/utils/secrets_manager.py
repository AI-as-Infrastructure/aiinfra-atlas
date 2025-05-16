"""
Secrets Manager for ATLAS application.

This module provides a consistent way to access secrets across different environments
(development, staging, production). It reads secrets from file-based storage.
"""
import os
import logging
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# Define paths relative to project root
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
CONFIG_DIR = os.path.join(PROJECT_ROOT, 'config')

# Load non-sensitive configuration from config/.env
ENV_FILE = os.path.join(CONFIG_DIR, '.env')
if os.path.exists(ENV_FILE):
    load_dotenv(ENV_FILE)
else:
    logger.error(f"Configuration file not found: {ENV_FILE}")

# Path to secrets file
SECRETS_FILE = os.path.join(CONFIG_DIR, '.secrets')

def get_config(config_name, default=None):
    """
    Get a configuration value from the config/.env file.
    
    Args:
        config_name (str): Name of the configuration to retrieve
        default (Any, optional): Default value if configuration is not found
        
    Returns:
        str or default: The configuration value or the default if not found
    """
    # First check if the value is in the environment (loaded from .env file)
    value = os.environ.get(config_name)
    if value is not None:
        return value
    
    # If not found in environment, try to read from .env file directly
    try:
        with open(ENV_FILE, "r") as f:
            for line in f:
                line = line.strip()
                # Skip comments and empty lines
                if not line or line.startswith("#"):
                    continue
                    
                if "=" in line:
                    key, value = line.split("=", 1)
                    if key.strip() == config_name:
                        # Remove quotes if present
                        value = value.strip()
                        if value.startswith('"') and value.endswith('"'):
                            value = value[1:-1]
                        return value
    except (FileNotFoundError, PermissionError) as e:
        logger.error(f"Configuration file not found or not readable: {ENV_FILE}")
    
    return default

def get_secret(secret_name, default=None):
    """
    Get a secret from various sources in order of priority:
    1. Environment variables
    2. .secrets file
    3. .env file (for non-sensitive configs that might be accessed via get_secret)
    
    Args:
        secret_name (str): Name of the secret to retrieve
        default (Any, optional): Default value if secret is not found
        
    Returns:
        str or default: The secret value or the default if not found
    """
    # First check environment variables
    env_value = os.environ.get(secret_name)
    if env_value is not None:
        return env_value
    
    # Then check .secrets file
    try:
        if os.path.exists(SECRETS_FILE):
            with open(SECRETS_FILE, "r") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#"):
                        if "=" in line:
                            key, value = line.split("=", 1)
                            key = key.strip()
                            if key == secret_name:
                                # Remove quotes if present
                                value = value.strip()
                                if value.startswith('"') and value.endswith('"'):
                                    value = value[1:-1]
                                return value
    except Exception as e:
        logger.warning(f"Secret {secret_name} not found in .secrets file: {str(e)}")
    
    # If not found in .secrets, also check .env file for non-sensitive configurations
    # This allows get_secret to work even for items moved to .env
    env_value = get_config(secret_name)
    if env_value is not None:
        return env_value
    
    # Log a warning that the secret was not found anywhere
    logger.warning(f"Secret {secret_name} not found")
    return default