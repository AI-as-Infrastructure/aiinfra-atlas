"""
Runtime mode management for ATLAS.

This module provides singleton mode management that persists for the lifetime
of the server process. Modes control whether the system allows configuration
changes or operates in locked deployment mode.
"""

import json
import logging
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


class SystemMode(Enum):
    """System operational modes."""
    CONFIGURE = "configure"  # Allow configuration changes
    DEPLOY = "deploy"        # Locked for deployment, no changes allowed


class ModeManager:
    """
    Singleton managing runtime mode state.

    The mode persists for the lifetime of the server process.
    Deploy mode is one-way - requires server restart to change.
    """

    _instance = None
    _mode: Optional[SystemMode] = None
    _locked_at: Optional[datetime] = None
    _locked_by: Optional[str] = None

    def __new__(cls):
        """Ensure singleton instance."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def get_mode(self) -> SystemMode:
        """
        Get current mode, defaulting to configure if not set.

        Returns:
            SystemMode: Current system mode
        """
        if self._mode is None:
            # Default to configure mode on startup
            # This allows users to choose their mode
            self._mode = SystemMode.CONFIGURE
            logger.info("Mode manager initialized in CONFIGURE mode")
        return self._mode

    def set_mode(self, mode: SystemMode, user_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Set system mode.

        Deploy mode is one-way - once set, it cannot be changed without
        restarting the server. This ensures configuration consistency
        during testing sessions.

        Args:
            mode: The mode to set
            user_id: Optional ID of user making the change

        Returns:
            Dict with mode status information

        Raises:
            ValueError: If trying to change from deploy mode
        """
        if self._mode == SystemMode.DEPLOY:
            raise ValueError(
                "Cannot change mode once in deploy mode. "
                "Server restart required to modify configuration."
            )

        self._mode = mode

        if mode == SystemMode.DEPLOY:
            self._locked_at = datetime.now()
            self._locked_by = user_id
            logger.info(
                f"System entered DEPLOY mode by user {user_id} at {self._locked_at}"
            )

        return {
            "mode": mode.value,
            "locked": mode == SystemMode.DEPLOY,
            "locked_at": self._locked_at.isoformat() if self._locked_at else None,
            "locked_by": self._locked_by
        }

    def is_locked(self) -> bool:
        """Check if system is in locked deploy mode."""
        return self.get_mode() == SystemMode.DEPLOY

    def has_complete_configuration(self) -> bool:
        """
        Check if system has complete configuration for deployment.

        Returns:
            bool: True if corpus and at least one target exist
        """
        config_path = Path("backend/config/atlas_config.json")

        # First check if the new centralized config exists
        if config_path.exists():
            try:
                with open(config_path) as f:
                    config = json.load(f)

                has_corpus = bool(config.get("corpus"))
                has_targets = bool(
                    config.get("targets", {}).get("configurations", {})
                )

                logger.debug(f"Configuration check: corpus={has_corpus}, targets={has_targets}")
                return has_corpus and has_targets

            except Exception as e:
                logger.error(f"Error checking centralized configuration: {e}")

        # Fallback: Check for traditional setup
        # Check if corpus exists (manifest.json)
        corpus_path = Path("backend/corpus/manifest.json")
        has_corpus = corpus_path.exists()

        # Check if any target files exist
        targets_path = Path("backend/targets")
        has_targets = False
        if targets_path.exists():
            target_files = list(targets_path.glob("*.txt"))
            # Filter out template files
            target_files = [f for f in target_files if not f.name.startswith("_") and not f.name.startswith(".")]
            has_targets = len(target_files) > 0

        logger.debug(f"Legacy configuration check: corpus={has_corpus}, targets={has_targets}")
        return has_corpus and has_targets

    def get_status(self) -> Dict[str, Any]:
        """
        Get complete mode status information.

        Returns:
            Dict with mode, lock status, and configuration state
        """
        return {
            "mode": self.get_mode().value,
            "locked": self.is_locked(),
            "locked_at": self._locked_at.isoformat() if self._locked_at else None,
            "locked_by": self._locked_by,
            "config_complete": self.has_complete_configuration()
        }

    def reset(self) -> None:
        """
        Reset mode manager state.

        This is primarily for testing purposes.
        In production, mode reset happens on server restart.
        """
        self._mode = None
        self._locked_at = None
        self._locked_by = None
        logger.info("Mode manager state reset")


# Global singleton instance
mode_manager = ModeManager()