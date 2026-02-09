"""
System Configuration Module

Manages runtime configuration for telemetry and inter-rater feedback settings.
Provides read/write access to system_settings.json and merges with environment variables.
"""

import json
import os
from pathlib import Path
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

class SystemConfiguration:
    """Manages system configuration settings."""

    DEFAULT_CONFIG = {
        "telemetryEnabled": False,
        "interRaterEnabled": False
    }

    def __init__(self, config_path: str = "config/system_settings.json"):
        """
        Initialize system configuration manager.

        Args:
            config_path: Path to the configuration file
        """
        self.config_path = Path(config_path)
        self.config = self._load_config()

    def _load_config(self) -> Dict[str, Any]:
        """
        Load configuration from file with defaults and environment overrides.

        Returns:
            Merged configuration dictionary
        """
        config = self.DEFAULT_CONFIG.copy()

        # Load from file if exists
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r') as f:
                    file_config = json.load(f)
                    config.update(file_config)
                    logger.info(f"Loaded system configuration from {self.config_path}")
            except Exception as e:
                logger.error(f"Failed to load config from {self.config_path}: {e}")
        else:
            logger.info(f"No config file found at {self.config_path}, using defaults")

        # Environment variables can override file settings
        # Check for ENABLE_TELEMETRY environment variable
        if os.getenv('ENABLE_TELEMETRY'):
            config['telemetryEnabled'] = os.getenv('ENABLE_TELEMETRY', '').lower() in ('true', '1', 'yes')
            logger.info(f"Telemetry overridden by environment: {config['telemetryEnabled']}")

        # Check for ENABLE_INTER_RATER environment variable
        if os.getenv('ENABLE_INTER_RATER'):
            config['interRaterEnabled'] = os.getenv('ENABLE_INTER_RATER', '').lower() in ('true', '1', 'yes')
            logger.info(f"Inter-rater feedback overridden by environment: {config['interRaterEnabled']}")

        return config

    def save_config(self, config: Dict[str, Any]) -> bool:
        """
        Save configuration to file.

        Args:
            config: Configuration dictionary to save

        Returns:
            Success status
        """
        try:
            # Ensure config directory exists
            self.config_path.parent.mkdir(parents=True, exist_ok=True)

            # Validate configuration
            validated_config = {
                "telemetryEnabled": bool(config.get("telemetryEnabled", False)),
                "interRaterEnabled": bool(config.get("interRaterEnabled", False))
            }

            # Save to file
            with open(self.config_path, 'w') as f:
                json.dump(validated_config, f, indent=2)

            # Update in-memory config
            self.config = validated_config
            logger.info(f"Saved system configuration to {self.config_path}")

            return True
        except Exception as e:
            logger.error(f"Failed to save configuration: {e}")
            return False

    def get_config(self) -> Dict[str, Any]:
        """
        Get current configuration.

        Returns:
            Current configuration dictionary
        """
        return self.config.copy()

    def update_config(self, updates: Dict[str, Any]) -> bool:
        """
        Update configuration with partial updates.

        Args:
            updates: Dictionary of configuration updates

        Returns:
            Success status
        """
        try:
            new_config = self.config.copy()
            new_config.update(updates)
            return self.save_config(new_config)
        except Exception as e:
            logger.error(f"Failed to update configuration: {e}")
            return False

    def is_telemetry_enabled(self) -> bool:
        """Check if telemetry is enabled."""
        return self.config.get("telemetryEnabled", False)

    def is_inter_rater_enabled(self) -> bool:
        """Check if inter-rater feedback is enabled."""
        return self.config.get("interRaterEnabled", False)

    def reload(self) -> None:
        """Reload configuration from file."""
        self.config = self._load_config()
        logger.info("Reloaded system configuration")

# Singleton instance
_system_config = None

def get_system_config() -> SystemConfiguration:
    """
    Get singleton instance of system configuration.

    Returns:
        SystemConfiguration instance
    """
    global _system_config
    if _system_config is None:
        _system_config = SystemConfiguration()
    return _system_config

def is_telemetry_enabled() -> bool:
    """Convenience function to check telemetry status."""
    return get_system_config().is_telemetry_enabled()

def is_inter_rater_enabled() -> bool:
    """Convenience function to check inter-rater feedback status."""
    return get_system_config().is_inter_rater_enabled()