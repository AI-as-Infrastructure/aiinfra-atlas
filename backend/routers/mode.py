"""
API endpoints for runtime mode management.

Provides endpoints for checking and changing system operational mode
between configuration and deployment states.
"""

import json
import logging
from pathlib import Path
from datetime import datetime
from fastapi import APIRouter, Request, HTTPException, Depends
from fastapi.responses import JSONResponse
from typing import Dict, Any, Optional

from backend.modules.mode_manager import mode_manager, SystemMode
from backend.modules.auth import optional_user

logger = logging.getLogger(__name__)

router = APIRouter(tags=["mode"])


def get_user_id(request: Request, user: Optional[Dict] = Depends(optional_user)) -> str:
    """Extract user ID from request."""
    if user and user.get("user_id"):
        return user["user_id"]
    # Fallback for non-authenticated mode
    return "anonymous"


def get_corpus_info() -> Optional[Dict[str, Any]]:
    """Get information about the current corpus."""
    # Check new centralized config first
    config_path = Path("backend/config/atlas_config.json")
    if config_path.exists():
        try:
            with open(config_path) as f:
                config = json.load(f)
                if config.get("corpus"):
                    return config["corpus"]
        except Exception as e:
            logger.error(f"Error reading centralized config: {e}")

    # Fallback to manifest
    manifest_path = Path("backend/corpus/manifest.json")
    if manifest_path.exists():
        try:
            with open(manifest_path) as f:
                manifest = json.load(f)
                # Handle nested v1.2+ manifest format
                em = manifest.get("embedding_model")
                embedding_model = em.get("id") if isinstance(em, dict) else em
                vs = manifest.get("vector_store", {})
                collection_name = vs.get("collection_name") if isinstance(vs, dict) else manifest.get("collection_name")
                return {
                    "name": manifest.get("corpus_name", "Unknown"),
                    "collection_name": collection_name,
                    "embedding_model": embedding_model,
                    "document_count": manifest.get("statistics", {}).get("total_documents", 0)
                }
        except Exception as e:
            logger.error(f"Error reading manifest: {e}")

    return None


def get_targets_info() -> Dict[str, Any]:
    """Get information about configured targets."""
    targets = {}
    default_target = None

    # Check new centralized config first
    config_path = Path("backend/config/atlas_config.json")
    if config_path.exists():
        try:
            with open(config_path) as f:
                config = json.load(f)
                if config.get("targets"):
                    return {
                        "configurations": config["targets"].get("configurations", {}),
                        "default": config["targets"].get("default"),
                        "count": len(config["targets"].get("configurations", {}))
                    }
        except Exception as e:
            logger.error(f"Error reading centralized config: {e}")

    # Fallback to target files
    targets_path = Path("backend/targets")
    if targets_path.exists():
        target_files = list(targets_path.glob("*.txt"))
        # Filter out template files
        target_files = [f for f in target_files if not f.name.startswith("_") and not f.name.startswith(".")]

        for target_file in target_files:
            target_name = target_file.stem
            try:
                config = {}
                with open(target_file) as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("#") and "=" in line:
                            key, value = line.split("=", 1)
                            config[key.strip()] = value.strip().strip('"').strip("'")

                targets[target_name] = {
                    "llm_provider": config.get("LLM_PROVIDER"),
                    "llm_model": config.get("LLM_MODEL"),
                    "search_k": int(config.get("SEARCH_K", 20))
                }
            except Exception as e:
                logger.error(f"Error reading target {target_name}: {e}")

        # Try to determine default from environment
        import os
        default_target = os.getenv("TEST_TARGET")

    return {
        "configurations": targets,
        "default": default_target,
        "count": len(targets)
    }


@router.get("/api/mode/status")
async def get_mode_status() -> Dict[str, Any]:
    """
    Get current mode and configuration status.

    Returns comprehensive information about the system's operational mode,
    including whether configuration is complete and if the system is locked.

    Returns:
        Dict containing:
        - mode: Current mode (configure/deploy)
        - locked: Whether mode is locked (deploy mode)
        - config_complete: Whether configuration is ready for deployment
        - has_corpus: Whether a corpus exists
        - has_targets: Whether test targets exist
        - corpus_info: Information about current corpus (if exists)
        - target_count: Number of configured test targets
    """
    status = mode_manager.get_status()

    # Add configuration details
    corpus_info = get_corpus_info()
    targets_info = get_targets_info()

    status.update({
        "has_corpus": corpus_info is not None,
        "has_targets": targets_info["count"] > 0,
        "corpus_info": corpus_info,
        "target_count": targets_info["count"],
        "default_target": targets_info["default"]
    })

    return status


@router.post("/api/mode/deploy")
async def enter_deploy_mode(
    request: Request,
    user_id: str = Depends(get_user_id)
) -> Dict[str, Any]:
    """
    Transition to deploy mode (one-way operation).

    This is a one-way operation that locks the system configuration.
    Once in deploy mode, the server must be restarted to make changes.

    Args:
        request: FastAPI request object
        user_id: Authenticated user ID

    Returns:
        Dict with mode transition confirmation

    Raises:
        HTTPException 400: If configuration is incomplete or already in deploy mode
    """
    # Validate configuration is complete
    if not mode_manager.has_complete_configuration():
        raise HTTPException(
            status_code=400,
            detail="Cannot enter deploy mode without complete configuration. "
                   "Please ensure you have built a corpus and configured at least one test target."
        )

    try:
        # Create corpus_active.json from manifest before entering deploy mode
        manifest_path = Path("backend/corpus/manifest.json")
        if manifest_path.exists():
            try:
                with open(manifest_path) as f:
                    manifest = json.load(f)

                # Extract essential information from manifest
                corpus_name = manifest.get("corpus_name", "corpus")

                # Get the first available target configuration
                targets_path = Path("backend/targets")
                target_name = "k20_claude_3_5_haiku_20241022"  # Default target

                # Find the first non-template target file
                if targets_path.exists():
                    for target_file in targets_path.glob("*.txt"):
                        if not target_file.name.startswith("_") and not target_file.name.startswith("."):
                            target_name = target_file.stem
                            break

                # Create minimal corpus_active.json configuration
                # Most information will be read from manifest.json at runtime
                corpus_active_config = {
                    "corpus_adapter": f"{corpus_name}_adapter",
                    "target": target_name,
                    "corpus_name": corpus_name,
                    "collection_name": manifest.get("vector_store", {}).get("collection_name", f"{corpus_name}_c"),
                    "corpus_path": "backend/corpus",
                    "chroma_persist_directory": "backend/corpus/chroma_db",
                    "embedding_model": manifest.get("embedding_model", {}).get("id", "sentence-transformers/all-MiniLM-L6-v2"),
                    "manifest_path": "backend/corpus/manifest.json",
                    "last_updated": datetime.now().isoformat(),
                    "created_by": "deployment_mode"
                }

                # Include facets from manifest v1.5+ if present
                facets = manifest.get("facets", [])
                if facets:
                    corpus_active_config["facets"] = facets

                # Write corpus_active.json
                corpus_active_path = Path("backend/corpus/corpus_active.json")
                with open(corpus_active_path, 'w') as f:
                    json.dump(corpus_active_config, f, indent=2)
                logger.info(f"Created corpus_active.json for deployment with corpus '{corpus_name}' and target '{target_name}'")

                # Force config cache to reinitialize immediately
                # so the new corpus_active.json and retriever are ready
                import backend.modules.config as config_module
                config_module._config = None
                config_module._retriever = None
                config_module._retriever_instance = None
                logger.info("Cleared config cache for retriever reinit")

                # Invalidate manifest cache
                from backend.modules.manifest_loader import invalidate_cache
                invalidate_cache()

                # Proactively reinitialize config and retriever now
                # so they're ready when the frontend makes its next request
                try:
                    config_module.initialize_config()
                    logger.info("Config and retriever reinitialized successfully")
                except Exception as reinit_err:
                    logger.warning(f"Config reinit warning (will retry on next request): {reinit_err}")

            except Exception as e:
                logger.error(f"Failed to create corpus_active.json: {e}")
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to activate corpus configuration: {e}"
                )
        else:
            raise HTTPException(
                status_code=400,
                detail="No corpus found. Please build a corpus using the wizard first."
            )

        # Set mode (one-way transition)
        result = mode_manager.set_mode(SystemMode.DEPLOY, user_id)

        # Log the transition for audit trail
        logger.info(f"System entered deploy mode by user {user_id}: {result}")

        return {
            **result,
            "message": "Successfully entered deploy mode. Configuration is now locked."
        }

    except ValueError as e:
        # Already in deploy mode
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/api/mode/configure")
async def enter_configure_mode(
    request: Request,
    user_id: str = Depends(get_user_id)
) -> Dict[str, Any]:
    """
    Enter or remain in configure mode.

    This endpoint is idempotent - calling it in configure mode is safe.
    However, it cannot be used to exit deploy mode.

    Args:
        user_id: Authenticated user ID

    Returns:
        Dict with mode status

    Raises:
        HTTPException 400: If currently in deploy mode
    """
    if mode_manager.is_locked():
        raise HTTPException(
            status_code=400,
            detail="Cannot change from deploy mode without server restart. "
                   "Please restart the server to modify configuration."
        )

    # Set or confirm configure mode
    result = mode_manager.set_mode(SystemMode.CONFIGURE, user_id)

    return {
        **result,
        "message": "System is in configuration mode"
    }


@router.get("/api/mode/can-configure")
async def can_configure() -> Dict[str, bool]:
    """
    Check if configuration changes are allowed.

    Simple endpoint for UI to check if configuration options
    should be enabled or disabled.

    Returns:
        Dict with can_configure boolean
    """
    return {
        "can_configure": not mode_manager.is_locked()
    }