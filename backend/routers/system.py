"""
System Configuration Router

Provides API endpoints for managing system-wide configuration settings.
"""

from fastapi import APIRouter, HTTPException, Body
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Dict, Any
import logging

from backend.modules.system_configuration import get_system_config

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/system", tags=["system"])

class SystemConfigRequest(BaseModel):
    """Request model for system configuration updates."""
    telemetryEnabled: bool = False
    interRaterEnabled: bool = False

@router.post("/configuration")
async def update_system_configuration(config: SystemConfigRequest):
    """
    Update system configuration settings.

    Args:
        config: System configuration settings

    Returns:
        Success response with current configuration
    """
    try:
        system_config = get_system_config()

        # Convert Pydantic model to dict
        config_dict = config.dict()

        # Save the configuration
        success = system_config.save_config(config_dict)

        if not success:
            raise HTTPException(
                status_code=500,
                detail="Failed to save configuration"
            )

        # Log the configuration change
        logger.info(f"System configuration updated: {config_dict}")

        # Return current configuration
        return JSONResponse({
            "success": True,
            "message": "Configuration updated successfully",
            "config": system_config.get_config()
        })

    except Exception as e:
        logger.error(f"Failed to update system configuration: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Configuration update failed: {str(e)}"
        )

@router.get("/configuration")
async def get_system_configuration():
    """
    Get current system configuration.

    Returns:
        Current system configuration settings
    """
    try:
        system_config = get_system_config()
        return JSONResponse({
            "config": system_config.get_config(),
            "telemetryEnabled": system_config.is_telemetry_enabled(),
            "interRaterEnabled": system_config.is_inter_rater_enabled()
        })

    except Exception as e:
        logger.error(f"Failed to get system configuration: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve configuration: {str(e)}"
        )

@router.post("/configuration/reload")
async def reload_system_configuration():
    """
    Reload system configuration from file.

    Returns:
        Success response with current configuration
    """
    try:
        system_config = get_system_config()
        system_config.reload()

        logger.info("System configuration reloaded")

        return JSONResponse({
            "success": True,
            "message": "Configuration reloaded successfully",
            "config": system_config.get_config()
        })

    except Exception as e:
        logger.error(f"Failed to reload system configuration: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Configuration reload failed: {str(e)}"
        )