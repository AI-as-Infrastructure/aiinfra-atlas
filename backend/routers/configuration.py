"""
Configuration Export/Import Router

Provides API endpoints for exporting and importing ATLAS configurations.
"""

from fastapi import APIRouter, HTTPException, UploadFile, File, Body
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Dict, Any, Optional
import json
import logging
import io

from backend.modules.configuration_export import get_configuration_exporter
from backend.modules.configuration_import import get_configuration_importer

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/configuration", tags=["configuration"])

class ExportRequest(BaseModel):
    """Request model for configuration export."""
    config_name: Optional[str] = None
    description: Optional[str] = None

@router.get("/export")
async def export_configuration(config_name: Optional[str] = None, description: Optional[str] = None):
    """
    Export current ATLAS configuration.

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

        # Return as JSON response
        return JSONResponse(
            content=export_config,
            headers={
                "Content-Disposition": f'attachment; filename="atlas_config_{export_config["exported_at"][:10]}.json"'
            }
        )

    except Exception as e:
        logger.error(f"Failed to export configuration: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Configuration export failed: {str(e)}"
        )

@router.post("/import")
async def import_configuration(file: UploadFile = File(...)):
    """
    Import and apply an ATLAS configuration.

    Args:
        file: Uploaded JSON configuration file

    Returns:
        Import result with success status and any warnings/errors
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
            raise HTTPException(
                status_code=400,
                detail=f"Invalid JSON file: {str(e)}"
            )

        # Import configuration
        importer = get_configuration_importer()
        success, result = importer.import_configuration(config_data)

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
        logger.error(f"Failed to import configuration: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Configuration import failed: {str(e)}"
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
            return JSONResponse(
                content={
                    "valid": False,
                    "errors": [f"Invalid JSON: {str(e)}"],
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
        logger.error(f"Failed to validate configuration: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Configuration validation failed: {str(e)}"
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
        logger.error(f"Failed to get current configuration: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve configuration: {str(e)}"
        )