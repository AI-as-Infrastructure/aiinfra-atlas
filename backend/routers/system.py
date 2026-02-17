"""
System Configuration Router

Provides API endpoints for managing system-wide configuration settings.
"""

from fastapi import APIRouter, HTTPException, Body, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict
from typing import Dict, Any
import logging
import time
from collections import defaultdict, deque

from backend.modules.system_configuration import get_system_config
from backend.modules.auth import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/system", tags=["system"])

CONFIG_WINDOW_SECONDS = 60
CONFIG_RATE_LIMIT = 20
_config_requests = defaultdict(deque)


def _user_identifier(user: dict) -> str:
    if not isinstance(user, dict):
        return "anonymous"
    return str(user.get("sub") or user.get("username") or user.get("email") or "anonymous")


def _check_config_rate_limit(user_key: str) -> bool:
    now = time.time()
    request_times = _config_requests[user_key]
    while request_times and now - request_times[0] > CONFIG_WINDOW_SECONDS:
        request_times.popleft()

    if len(request_times) >= CONFIG_RATE_LIMIT:
        return False

    request_times.append(now)
    return True

class SystemConfigRequest(BaseModel):
    """Request model for system configuration updates."""
    model_config = ConfigDict(extra="forbid", strict=True)

    telemetryEnabled: bool = False
    interRaterEnabled: bool = False

@router.post("/configuration")
async def update_system_configuration(
    config: SystemConfigRequest,
    user: dict = Depends(get_current_user)
):
    """
    Update system configuration settings.

    Args:
        config: System configuration settings

    Returns:
        Success response with current configuration
    """
    try:
        user_key = _user_identifier(user)
        if not _check_config_rate_limit(user_key):
            raise HTTPException(
                status_code=429,
                detail="Too many configuration updates. Please wait before retrying."
            )

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
        logger.info(
            "System configuration updated",
            extra={
                "user": user_key,
                "telemetryEnabled": config_dict.get("telemetryEnabled"),
                "interRaterEnabled": config_dict.get("interRaterEnabled"),
            },
        )

        # Return current configuration
        return JSONResponse({
            "success": True,
            "message": "Configuration updated successfully",
            "config": system_config.get_config()
        })

    except HTTPException:
        raise
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

    except HTTPException:
        raise
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

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to reload system configuration: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Configuration reload failed: {str(e)}"
        )