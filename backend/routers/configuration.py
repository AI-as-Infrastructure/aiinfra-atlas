"""
Configuration Export/Import Router

Provides API endpoints for exporting and importing ATLAS configurations.
"""

from fastapi import APIRouter, HTTPException, UploadFile, File, Body, Depends
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel
from typing import Dict, Any, Optional
import json
import gzip
import logging
import io
import time
from collections import defaultdict, deque

from backend.modules.configuration_export import get_configuration_exporter
from backend.modules.configuration_import import get_configuration_importer
from backend.modules.auth import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/configuration", tags=["configuration"])

IMPORT_WINDOW_SECONDS = 60
IMPORT_RATE_LIMIT = 10
_import_requests = defaultdict(deque)


def _user_identifier(user: dict) -> str:
    if not isinstance(user, dict):
        return "anonymous"
    return str(user.get("sub") or user.get("username") or user.get("email") or "anonymous")


def _check_import_rate_limit(user_key: str) -> bool:
    now = time.time()
    request_times = _import_requests[user_key]
    while request_times and now - request_times[0] > IMPORT_WINDOW_SECONDS:
        request_times.popleft()

    if len(request_times) >= IMPORT_RATE_LIMIT:
        return False

    request_times.append(now)
    return True

class ExportRequest(BaseModel):
    """Request model for configuration export."""
    config_name: Optional[str] = None
    description: Optional[str] = None

@router.get("/export")
async def export_configuration(
    config_name: Optional[str] = None,
    description: Optional[str] = None,
    compress: bool = False,
    user: dict = Depends(get_current_user)
):
    """
    Export current ATLAS configuration. Requires authentication when Cognito is enabled.

    Args:
        config_name: Optional name for the configuration
        description: Optional description for the configuration

    Returns:
        JSON configuration ready for download
    """
    try:
        exporter = get_configuration_exporter()

        # Build export configuration
        export_config = exporter.build_export_json(config_name, description)

        filename_base = f"atlas_config_{export_config['exported_at'][:10]}"

        if compress:
            payload = json.dumps(export_config, separators=(",", ":")).encode("utf-8")
            compressed_payload = gzip.compress(payload)
            return Response(
                content=compressed_payload,
                media_type="application/gzip",
                headers={
                    "Content-Disposition": f'attachment; filename="{filename_base}.json.gz"'
                },
            )

        # Return as JSON response
        return JSONResponse(
            content=export_config,
            headers={
                "Content-Disposition": f'attachment; filename="{filename_base}.json"'
            }
        )

    except Exception as e:
        logger.error(f"Failed to export configuration: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Configuration export failed"
        )

@router.post("/import")
async def import_configuration(
    file: UploadFile = File(...),
    user: dict = Depends(get_current_user)
):
    """
    Import and apply an ATLAS configuration. Requires authentication when Cognito is enabled.

    Args:
        file: Uploaded JSON configuration file

    Returns:
        Import result with success status and any warnings/errors
    """
    try:
        user_key = _user_identifier(user)
        if not _check_import_rate_limit(user_key):
            raise HTTPException(
                status_code=429,
                detail="Too many import attempts. Please wait before retrying."
            )

        # Check file size
        contents = await file.read()
        if len(contents) > 10 * 1024 * 1024:  # 10MB limit
            raise HTTPException(
                status_code=413,
                detail="Configuration file too large (max 10MB)"
            )

        # Parse JSON
        try:
            config_data = json.loads(contents)
        except json.JSONDecodeError as e:
            logger.warning(f"Invalid JSON in configuration import: {e}")
            raise HTTPException(
                status_code=400,
                detail="Invalid JSON file format"
            )

        # Import configuration
        importer = get_configuration_importer()
        success, result = importer.import_configuration(config_data)

        logger.info(
            "Configuration import requested",
            extra={
                "user": user_key,
                "success": success,
                "warnings": len(result.get("warnings", [])),
                "errors": len(result.get("errors", [])),
                "backup_path": result.get("backup_path"),
            },
        )

        if not success:
            # Return errors but don't fail completely
            return JSONResponse(
                content={
                    "success": False,
                    "message": "Configuration import partially failed",
                    **result
                },
                status_code=207  # Multi-Status
            )

        return JSONResponse({
            "success": True,
            "message": "Configuration imported successfully",
            **result
        })

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to import configuration: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Configuration import failed"
        )

@router.post("/validate")
async def validate_configuration(file: UploadFile = File(...)):
    """
    Validate an ATLAS configuration without applying it.

    Args:
        file: Uploaded JSON configuration file

    Returns:
        Validation result with any errors or warnings
    """
    try:
        # Check file size
        contents = await file.read()
        if len(contents) > 10 * 1024 * 1024:  # 10MB limit
            raise HTTPException(
                status_code=413,
                detail="Configuration file too large (max 10MB)"
            )

        # Parse JSON
        try:
            config_data = json.loads(contents)
        except json.JSONDecodeError as e:
            logger.warning(f"Invalid JSON in configuration validation: {e}")
            return JSONResponse(
                content={
                    "valid": False,
                    "errors": ["Invalid JSON file format"],
                    "warnings": []
                },
                status_code=400
            )

        # Validate configuration
        importer = get_configuration_importer()

        # Check structure
        is_valid, errors = importer.validate_import_structure(config_data)
        if not is_valid:
            return JSONResponse({
                "valid": False,
                "errors": errors,
                "warnings": []
            })

        # Check version compatibility
        is_compatible, message = importer.check_version_compatibility(config_data)
        if not is_compatible:
            return JSONResponse({
                "valid": False,
                "errors": [message],
                "warnings": []
            })

        # Check resources
        resources_valid, warnings = importer.validate_resources(config_data)

        # Add version warning if applicable
        if "Warning" in message:
            warnings.insert(0, message)

        return JSONResponse({
            "valid": True,
            "errors": [],
            "warnings": warnings,
            "config_name": config_data.get("config_name", "Unknown"),
            "description": config_data.get("description", ""),
            "exported_at": config_data.get("exported_at", ""),
            "atlas_version": config_data.get("atlas_version", "")
        })

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to validate configuration: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Configuration validation failed"
        )

@router.get("/current")
async def get_current_configuration():
    """
    Get the current configuration without exporting to file.

    Returns:
        Current configuration as JSON
    """
    try:
        exporter = get_configuration_exporter()

        # Gather all configurations
        config = {
            "corpus": exporter.gather_corpus_config(),
            "test_target": exporter.gather_target_config(),
            "system": exporter.gather_system_config()
        }

        return JSONResponse(config)

    except Exception as e:
        logger.error(f"Failed to get current configuration: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve configuration"
        )