"""
Error handling utilities for API endpoints.

This module provides utilities for consistent error handling across the application,
ensuring detailed errors are logged internally while generic messages are returned
to clients to prevent information leakage.
"""

import logging
import re
from typing import Optional, Any
from fastapi import HTTPException

logger = logging.getLogger(__name__)

# Pre-compiled regex patterns for error message sanitization
_UNIX_PATH_PATTERN = re.compile(r'/[^\s:]+')
_WINDOWS_PATH_PATTERN = re.compile(r'[A-Za-z]:\\[^\s:]+')
_LINE_NUMBER_PATTERN = re.compile(r'line \d+', re.IGNORECASE)
_COLON_LINE_PATTERN = re.compile(r':\d+:')
_FILE_REF_PATTERN = re.compile(r'File "[^"]+",')



def safe_http_error(
    exception: Exception,
    user_message: str,
    status_code: int = 400,
    log_level: str = "error",
    context: Optional[dict] = None
) -> HTTPException:
    """
    Log detailed error internally and raise HTTPException with generic message.

    Args:
        exception: The original exception that occurred
        user_message: Generic message to return to the client
        status_code: HTTP status code (default 400)
        log_level: Logging level - "error", "warning", or "info"
        context: Optional dict of additional context to log

    Returns:
        HTTPException with generic message

    Usage:
        try:
            # operation
        except Exception as e:
            raise safe_http_error(e, "Operation failed", 500)
    """
    # Build log message with context
    log_msg = f"{user_message}: {exception}"
    if context:
        log_msg += f" | Context: {context}"

    # Log at appropriate level
    if log_level == "warning":
        logger.warning(log_msg, exc_info=True)
    elif log_level == "info":
        logger.info(log_msg)
    else:
        logger.error(log_msg, exc_info=True)

    return HTTPException(status_code=status_code, detail=user_message)


def log_and_continue(
    exception: Exception,
    operation: str,
    default: Any = None,
    context: Optional[dict] = None
) -> Any:
    """
    Log an error and return a default value instead of raising.

    Use this for non-critical operations where failure shouldn't stop execution.

    Args:
        exception: The exception that occurred
        operation: Description of the failed operation
        default: Value to return on failure
        context: Optional dict of additional context to log

    Returns:
        The default value

    Usage:
        try:
            result = risky_operation()
        except Exception as e:
            result = log_and_continue(e, "loading optional config", default={})
    """
    log_msg = f"Non-critical error in {operation}: {exception}"
    if context:
        log_msg += f" | Context: {context}"

    logger.warning(log_msg, exc_info=False)  # Don't need full traceback for non-critical
    return default


def sanitize_error_message(message: str) -> str:
    """
    Remove potentially sensitive information from error messages.

    Removes:
    - File paths (anything starting with / or containing backslashes)
    - Line numbers
    - Stack trace references

    Args:
        message: The original error message

    Returns:
        Sanitized message safe for client display
    """
    # Remove absolute paths (using pre-compiled patterns for performance)
    sanitized = _UNIX_PATH_PATTERN.sub('[path]', message)

    # Remove Windows-style paths
    sanitized = _WINDOWS_PATH_PATTERN.sub('[path]', sanitized)

    # Remove line numbers like "line 42" or ":42:"
    sanitized = _LINE_NUMBER_PATTERN.sub('line [N]', sanitized)
    sanitized = _COLON_LINE_PATTERN.sub(':[N]:', sanitized)

    # Remove "File" references from tracebacks
    sanitized = _FILE_REF_PATTERN.sub('File "[path]",', sanitized)

    return sanitized


class ErrorContext:
    """
    Context manager for consistent error handling in API endpoints.

    Usage:
        async def my_endpoint():
            with ErrorContext("processing request", default_status=500):
                # operations that might fail
                return result
    """

    def __init__(
        self,
        operation: str,
        default_status: int = 500,
        default_message: Optional[str] = None
    ):
        self.operation = operation
        self.default_status = default_status
        self.default_message = default_message or f"Failed to {operation}"

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            # Don't catch HTTPExceptions - let them propagate
            if isinstance(exc_val, HTTPException):
                return False

            # Log and convert to HTTPException
            logger.error(
                f"Error during {self.operation}: {exc_val}",
                exc_info=True
            )
            raise HTTPException(
                status_code=self.default_status,
                detail=self.default_message
            )

        return False


# Standard error messages for common scenarios
ERROR_MESSAGES = {
    "analysis_failed": "Corpus analysis failed",
    "build_failed": "Corpus build failed",
    "validation_failed": "Validation failed",
    "config_import_failed": "Configuration import failed",
    "config_export_failed": "Configuration export failed",
    "target_not_found": "Target configuration not found",
    "invalid_path": "Invalid path specified",
    "invalid_identifier": "Invalid identifier format",
    "permission_denied": "Permission denied",
    "internal_error": "An internal error occurred",
}


def get_error_message(key: str, fallback: str = "Operation failed") -> str:
    """Get a standard error message by key."""
    return ERROR_MESSAGES.get(key, fallback)
