"""
Configuration Export Module

Handles exporting ATLAS configurations including corpus, target, and system settings.
"""

import json
import os
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

class ConfigurationExporter:
    """Manages configuration export functionality."""

    def __init__(self):
        """Initialize configuration exporter."""
        self.atlas_version = self._get_atlas_version()

    def _get_atlas_version(self) -> str:
        """Get ATLAS version from environment or default."""
        return os.getenv("ATLAS_VERSION", "1.0.0")

    def gather_corpus_config(self) -> Dict[str, Any]:
        """
        Gather current corpus configuration from corpus_active.json.

        Returns:
            Dictionary containing corpus configuration
        """
        corpus_config = {}

        try:
            # Read from corpus_active.json if it exists
            corpus_active_path = Path("backend/targets/corpus_active.json")
            if corpus_active_path.exists():
                with open(corpus_active_path, 'r') as f:
                    active_config = json.load(f)

                    # Extract relevant corpus configuration
                    corpus_config = {
                        "name": active_config.get("corpus_name", ""),
                        "retriever_module": active_config.get("retriever_module", ""),
                        "collection_name": active_config.get("collection_name", ""),
                        "embedding": {
                            "model": active_config.get("embedding_model", ""),
                            "chunk_size": active_config.get("chunk_size", 1500),
                            "chunk_overlap": active_config.get("chunk_overlap", 150),
                            "text_splitter_type": active_config.get("text_splitter_type", "RecursiveCharacterTextSplitter"),
                            "pooling": active_config.get("pooling", "mean")
                        },
                        "retrieval": {
                            "algorithm": active_config.get("algorithm", "hnsw"),
                            "large_retrieval_size_single": active_config.get("large_retrieval_size_single_corpus", 120),
                            "large_retrieval_size_all": active_config.get("large_retrieval_size_all_corpus", 80)
                        }
                    }

            # Try to read manifest for additional metadata
            manifest_path = Path("backend/corpus/manifest.json")
            if manifest_path.exists():
                with open(manifest_path, 'r') as f:
                    manifest = json.load(f)

                    # Add metadata from manifest
                    if "metadata" in manifest:
                        corpus_config["metadata"] = manifest["metadata"]

                    # Add source configuration
                    if "source" in manifest:
                        corpus_config["source"] = manifest["source"]

                    # Add filters
                    if "filters" in manifest:
                        corpus_config["filters"] = manifest["filters"]

            logger.info("Successfully gathered corpus configuration")

        except Exception as e:
            logger.error(f"Failed to gather corpus configuration: {e}")

        return corpus_config

    def gather_target_config(self) -> Dict[str, Any]:
        """
        Gather current test target configuration.

        Returns:
            Dictionary containing target configuration
        """
        target_config = {}

        try:
            # Get current TEST_TARGET from environment
            test_target = os.getenv("TEST_TARGET")

            if test_target:
                # Try to read the target file
                target_path = Path(f"backend/targets/{test_target}.txt")
                if target_path.exists():
                    config = {}
                    with open(target_path, 'r') as f:
                        for line in f:
                            line = line.strip()
                            if line and not line.startswith("#") and "=" in line:
                                key, value = line.split("=", 1)
                                config[key.strip()] = value.strip().strip('"').strip("'")

                    # Map to standard format
                    target_config = {
                        "id": test_target,
                        "provider": config.get("LLM_PROVIDER", ""),
                        "model": config.get("LLM_MODEL", ""),
                        "temperature": float(config.get("TEMPERATURE", 0.7)),
                        "max_tokens": int(config.get("MAX_TOKENS", 4096)),
                        "search_k": int(config.get("SEARCH_K", 20)),
                        "search_type": config.get("SEARCH_TYPE", "similarity"),
                        "search_score_threshold": float(config.get("SEARCH_SCORE_THRESHOLD", 0.7)),
                        "citation_limit": int(config.get("CITATION_LIMIT", 10))
                    }

            # Also check corpus_active.json for target info
            corpus_active_path = Path("backend/targets/corpus_active.json")
            if corpus_active_path.exists():
                with open(corpus_active_path, 'r') as f:
                    active_config = json.load(f)

                    # Override with active config if available
                    if "target_id" in active_config:
                        target_config["id"] = active_config["target_id"]
                    if "llm_provider" in active_config:
                        target_config["provider"] = active_config["llm_provider"]
                    if "llm_model" in active_config:
                        target_config["model"] = active_config["llm_model"]

            logger.info("Successfully gathered target configuration")

        except Exception as e:
            logger.error(f"Failed to gather target configuration: {e}")

        return target_config

    def gather_system_config(self) -> Dict[str, Any]:
        """
        Gather current system configuration settings.

        Returns:
            Dictionary containing system configuration
        """
        system_config = {}

        try:
            # Import system configuration module
            from backend.modules.system_configuration import get_system_config

            config = get_system_config()
            system_config = config.get_config()

            logger.info("Successfully gathered system configuration")

        except Exception as e:
            logger.error(f"Failed to gather system configuration: {e}")
            # Return defaults if module not available
            system_config = {
                "telemetryEnabled": False,
                "interRaterEnabled": False
            }

        return system_config

    def build_export_json(self,
                         config_name: Optional[str] = None,
                         description: Optional[str] = None) -> Dict[str, Any]:
        """
        Build complete configuration export JSON.

        Args:
            config_name: Optional name for the configuration
            description: Optional description for the configuration

        Returns:
            Complete configuration dictionary ready for export
        """
        # Generate default name if not provided
        if not config_name:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            config_name = f"ATLAS Configuration - {timestamp}"

        # Gather all configurations
        corpus_config = self.gather_corpus_config()
        target_config = self.gather_target_config()
        system_config = self.gather_system_config()

        # Build export structure
        export_config = {
            "atlas_config_version": "1.0",
            "exported_at": datetime.now().isoformat(),
            "atlas_version": self.atlas_version,
            "config_name": config_name,
            "description": description or "",
            "corpus": corpus_config,
            "test_target": target_config,
            "system": system_config
        }

        logger.info(f"Built configuration export: {config_name}")

        return export_config

    def export_to_file(self,
                       filepath: Path,
                       config_name: Optional[str] = None,
                       description: Optional[str] = None) -> bool:
        """
        Export configuration to a JSON file.

        Args:
            filepath: Path where to save the configuration
            config_name: Optional name for the configuration
            description: Optional description for the configuration

        Returns:
            Success status
        """
        try:
            # Build export configuration
            export_config = self.build_export_json(config_name, description)

            # Write to file
            with open(filepath, 'w') as f:
                json.dump(export_config, f, indent=2)

            logger.info(f"Exported configuration to {filepath}")
            return True

        except Exception as e:
            logger.error(f"Failed to export configuration: {e}")
            return False

# Singleton instance
_exporter = None

def get_configuration_exporter() -> ConfigurationExporter:
    """
    Get singleton instance of configuration exporter.

    Returns:
        ConfigurationExporter instance
    """
    global _exporter
    if _exporter is None:
        _exporter = ConfigurationExporter()
    return _exporter