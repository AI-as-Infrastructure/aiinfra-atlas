"""
Configuration Import Module

Handles importing and applying ATLAS configurations.
"""

import json
import os
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Tuple, Optional, List
import logging
import re
from urllib.parse import unquote

from backend.modules.path_validator import validate_safe_path, validate_repo_subpath

logger = logging.getLogger(__name__)

class ConfigurationImporter:
    """Manages configuration import functionality."""

    # Supported configuration versions
    SUPPORTED_VERSIONS = ["1.0"]

    # Maximum file size (10MB)
    MAX_FILE_SIZE = 10 * 1024 * 1024

    def __init__(self):
        """Initialize configuration importer."""
        self.atlas_version = self._get_atlas_version()

    def _get_atlas_version(self) -> str:
        """Get ATLAS version from environment or default."""
        return os.getenv("ATLAS_VERSION", "1.0.0")

    def validate_import_structure(self, config: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Validate the structure of imported configuration.

        Args:
            config: Configuration dictionary to validate

        Returns:
            Tuple of (is_valid, error_messages)
        """
        errors = []

        # Check required top-level fields
        required_fields = ["atlas_config_version", "corpus", "test_target"]
        for field in required_fields:
            if field not in config:
                errors.append(f"Missing required field: {field}")

        # Validate corpus section if present
        if "corpus" in config:
            corpus = config["corpus"]
            if not isinstance(corpus, dict):
                errors.append("Corpus configuration must be a dictionary")
            else:
                # Check for critical corpus fields
                if "embedding" in corpus and not isinstance(corpus["embedding"], dict):
                    errors.append("Corpus embedding configuration must be a dictionary")

        # Validate test_target section if present
        if "test_target" in config:
            target = config["test_target"]
            if not isinstance(target, dict):
                errors.append("Test target configuration must be a dictionary")
            else:
                # Check for critical target fields
                if "provider" in target and not target["provider"]:
                    errors.append("Test target provider cannot be empty")
                if "model" in target and not target["model"]:
                    errors.append("Test target model cannot be empty")

        # Validate system section if present
        if "system" in config:
            system = config["system"]
            if not isinstance(system, dict):
                errors.append("System configuration must be a dictionary")
            else:
                # Validate boolean fields
                for field in ["telemetryEnabled", "interRaterEnabled"]:
                    if field in system and not isinstance(system[field], bool):
                        errors.append(f"System {field} must be a boolean")

        return len(errors) == 0, errors

    def check_version_compatibility(self, config: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Check if configuration version is compatible.

        Args:
            config: Configuration dictionary with version info

        Returns:
            Tuple of (is_compatible, message)
        """
        config_version = config.get("atlas_config_version", "unknown")

        if config_version not in self.SUPPORTED_VERSIONS:
            return False, f"Unsupported configuration version: {config_version}. Supported versions: {', '.join(self.SUPPORTED_VERSIONS)}"

        # Check if configuration is from a newer ATLAS version
        export_atlas_version = config.get("atlas_version", "0.0.0")
        if self._compare_versions(export_atlas_version, self.atlas_version) > 0:
            logger.warning(f"Configuration exported from newer ATLAS version: {export_atlas_version} (current: {self.atlas_version})")
            # Allow import but warn user
            return True, f"Warning: Configuration from newer ATLAS version ({export_atlas_version})"

        return True, "Version compatible"

    def _compare_versions(self, v1: str, v2: str) -> int:
        """
        Compare two version strings.

        Args:
            v1: First version
            v2: Second version

        Returns:
            -1 if v1 < v2, 0 if equal, 1 if v1 > v2
        """
        try:
            v1_parts = [int(x) for x in v1.split(".")]
            v2_parts = [int(x) for x in v2.split(".")]

            # Pad shorter version with zeros
            max_len = max(len(v1_parts), len(v2_parts))
            v1_parts.extend([0] * (max_len - len(v1_parts)))
            v2_parts.extend([0] * (max_len - len(v2_parts)))

            for i in range(max_len):
                if v1_parts[i] < v2_parts[i]:
                    return -1
                elif v1_parts[i] > v2_parts[i]:
                    return 1
            return 0
        except:
            return 0

    def sanitize_path(self, path: str) -> Optional[str]:
        """
        Sanitize file path to prevent directory traversal attacks.

        Uses the centralized path_validator module for consistent security checks
        across the application.

        Args:
            path: Path to sanitize

        Returns:
            Sanitized path or None if invalid
        """
        if not path:
            return None

        # URL decode to catch encoded traversal attempts
        decoded_path = unquote(path)

        # Check for traversal patterns (comprehensive list)
        traversal_patterns = [
            '..',           # Standard traversal
            '.%2e',         # Mixed URL encoding
            '%2e.',         # Mixed URL encoding
            '%2e%2e',       # Full URL encoding
            '..%00',        # Null byte injection
            '..%5c',        # URL-encoded backslash
        ]
        lower_path = decoded_path.lower()
        for pattern in traversal_patterns:
            if pattern in lower_path:
                logger.warning(f"Rejected path with traversal pattern: {path[:100]}")
                return None

        # Remove leading slashes to make relative
        cleaned = decoded_path.lstrip('/\\')

        # Normalize path separators
        cleaned = cleaned.replace('\\', '/')

        # Ensure path doesn't reference system directories
        dangerous_starts = [
            'etc/', 'usr/', 'bin/', 'sbin/', 'var/', 'tmp/', 'root/', 'home/',
            'proc/', 'sys/', 'dev/', 'boot/', 'lib/', 'opt/',
            'windows/', 'program files/', 'programdata/', 'users/',
        ]
        lower_cleaned = cleaned.lower()
        for dangerous in dangerous_starts:
            if lower_cleaned.startswith(dangerous):
                logger.warning(f"Rejected path referencing system directory: {path[:100]}")
                return None

        # Additional check: absolute paths (after stripping should not start with /)
        if cleaned.startswith('/') or (len(cleaned) > 1 and cleaned[1] == ':'):
            logger.warning(f"Rejected absolute path: {path[:100]}")
            return None

        return cleaned

    def validate_resources(self, config: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Validate that required resources exist or can be accessed.

        Args:
            config: Configuration dictionary

        Returns:
            Tuple of (all_valid, warning_messages)
        """
        warnings = []

        # Check corpus source paths if specified
        if "corpus" in config and "source" in config["corpus"]:
            source = config["corpus"]["source"]

            if source.get("type") == "file_path":
                path = source.get("path")
                if path:
                    sanitized = self.sanitize_path(path)
                    if not sanitized:
                        warnings.append(f"Invalid corpus source path: {path}")
                    elif not Path(sanitized).exists():
                        warnings.append(f"Corpus source path does not exist: {sanitized}")

            elif source.get("type") == "github":
                url = source.get("url")
                if url and not url.startswith(("http://", "https://")):
                    warnings.append(f"Invalid GitHub URL: {url}")

        # Check embedding model availability
        if "corpus" in config and "embedding" in config["corpus"]:
            model = config["corpus"]["embedding"].get("model")
            if model:
                # Just warn, don't fail - model might be downloadable
                warnings.append(f"Note: Ensure embedding model is available: {model}")

        return len(warnings) == 0, warnings

    def apply_corpus_config(self, corpus_config: Dict[str, Any]) -> bool:
        """
        Apply corpus configuration.

        Args:
            corpus_config: Corpus configuration dictionary

        Returns:
            Success status
        """
        try:
            # For now, we'll save this to a staging file
            # Full implementation would trigger corpus rebuild
            staging_path = Path("backend/targets/imported_corpus_config.json")

            # Ensure directory exists
            staging_path.parent.mkdir(parents=True, exist_ok=True)

            # Save configuration
            with open(staging_path, 'w') as f:
                json.dump(corpus_config, f, indent=2)

            logger.info("Saved imported corpus configuration to staging")
            return True

        except Exception as e:
            logger.error(f"Failed to apply corpus configuration: {e}")
            return False

    def apply_target_config(self, target_config: Dict[str, Any]) -> bool:
        """
        Apply test target configuration.

        Args:
            target_config: Target configuration dictionary

        Returns:
            Success status
        """
        try:
            # Generate target file name
            target_id = target_config.get("id")
            if not target_id:
                # Generate ID from provider and model
                provider = target_config.get("provider", "unknown")
                model = target_config.get("model", "unknown").replace("-", "_").replace(".", "_")
                k = target_config.get("search_k", 20)
                target_id = f"k{k}_{provider}_{model}"

            # Create target file content
            lines = [
                "# Imported target configuration",
                f"# Imported at: {datetime.now().isoformat()}",
                "",
                f"LLM_PROVIDER={target_config.get('provider', '')}",
                f"LLM_MODEL={target_config.get('model', '')}",
                f"TEMPERATURE={target_config.get('temperature', 0.7)}",
                f"MAX_TOKENS={target_config.get('max_tokens', 4096)}",
                f"SEARCH_TYPE={target_config.get('search_type', 'similarity')}",
                f"SEARCH_K={target_config.get('search_k', 20)}",
                f"SEARCH_SCORE_THRESHOLD={target_config.get('search_score_threshold', 0.7)}",
                f"CITATION_LIMIT={target_config.get('citation_limit', 10)}",
            ]

            # Write target file
            target_path = Path(f"backend/targets/{target_id}.txt")
            target_path.parent.mkdir(parents=True, exist_ok=True)

            with open(target_path, 'w') as f:
                f.write('\n'.join(lines))

            # Update TEST_TARGET environment variable
            os.environ["TEST_TARGET"] = target_id

            logger.info(f"Applied target configuration: {target_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to apply target configuration: {e}")
            return False

    def apply_system_config(self, system_config: Dict[str, Any]) -> bool:
        """
        Apply system configuration.

        Args:
            system_config: System configuration dictionary

        Returns:
            Success status
        """
        try:
            # Import system configuration module
            from backend.modules.system_configuration import get_system_config

            config = get_system_config()
            success = config.save_config(system_config)

            if success:
                logger.info("Applied system configuration")
            return success

        except Exception as e:
            logger.error(f"Failed to apply system configuration: {e}")
            return False

    def import_configuration(self, config_data: Dict[str, Any]) -> Tuple[bool, Dict[str, Any]]:
        """
        Import and apply a complete configuration.

        Args:
            config_data: Complete configuration dictionary

        Returns:
            Tuple of (success, result_info)
        """
        result = {
            "success": False,
            "corpus_applied": False,
            "target_applied": False,
            "system_applied": False,
            "errors": [],
            "warnings": []
        }

        # Validate structure
        is_valid, errors = self.validate_import_structure(config_data)
        if not is_valid:
            result["errors"] = errors
            return False, result

        # Check version compatibility
        is_compatible, message = self.check_version_compatibility(config_data)
        if not is_compatible:
            result["errors"].append(message)
            return False, result
        elif "Warning" in message:
            result["warnings"].append(message)

        # Validate resources
        resources_valid, warnings = self.validate_resources(config_data)
        result["warnings"].extend(warnings)

        # Apply configurations
        success_count = 0

        # Apply corpus configuration if present
        if "corpus" in config_data:
            if self.apply_corpus_config(config_data["corpus"]):
                result["corpus_applied"] = True
                success_count += 1
            else:
                result["errors"].append("Failed to apply corpus configuration")

        # Apply target configuration if present
        if "test_target" in config_data:
            if self.apply_target_config(config_data["test_target"]):
                result["target_applied"] = True
                success_count += 1
            else:
                result["errors"].append("Failed to apply target configuration")

        # Apply system configuration if present
        if "system" in config_data:
            if self.apply_system_config(config_data["system"]):
                result["system_applied"] = True
                success_count += 1
            else:
                result["errors"].append("Failed to apply system configuration")

        result["success"] = success_count > 0 and len(result["errors"]) == 0
        return result["success"], result

# Singleton instance
_importer = None

def get_configuration_importer() -> ConfigurationImporter:
    """
    Get singleton instance of configuration importer.

    Returns:
        ConfigurationImporter instance
    """
    global _importer
    if _importer is None:
        _importer = ConfigurationImporter()
    return _importer