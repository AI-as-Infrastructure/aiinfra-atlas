"""
Path validation utilities for preventing directory traversal and injection attacks.

This module provides security utilities for validating user-provided paths,
identifiers, and other inputs that could be used in file system operations.
"""

import re
import logging
from pathlib import Path
from typing import Optional, Tuple
from urllib.parse import unquote

logger = logging.getLogger(__name__)

# Pre-compiled patterns for validation
SAFE_IDENTIFIER_PATTERN = re.compile(r'^[a-zA-Z0-9_-]+$')
SAFE_DISPLAY_NAME_PATTERN = re.compile(r'^[a-zA-Z0-9\s\-_\.,:;()\[\]]+$')
GITHUB_HOST_PATTERN = re.compile(r'^(www\.)?github\.com$', re.IGNORECASE)

# Dangerous path components that indicate traversal attempts
TRAVERSAL_PATTERNS = [
    '..',
    '.%2e',
    '%2e.',
    '%2e%2e',
]


def validate_safe_path(
    user_path: str,
    allowed_base: Path,
    must_exist: bool = False
) -> Path:
    """
    Validate that a user-provided path is within an allowed directory.

    Args:
        user_path: The path string provided by the user
        allowed_base: The base directory that paths must be within
        must_exist: If True, the path must exist on the filesystem

    Returns:
        The validated, resolved Path object

    Raises:
        ValueError: If the path is invalid or outside allowed bounds
    """
    if not user_path:
        raise ValueError("Path cannot be empty")

    # URL decode to catch encoded traversal attempts
    decoded_path = unquote(user_path)

    # Check for obvious traversal patterns before resolution
    lower_path = decoded_path.lower()
    for pattern in TRAVERSAL_PATTERNS:
        if pattern in lower_path:
            logger.warning(f"Path traversal attempt detected: {user_path[:100]}")
            raise ValueError("Invalid path: directory traversal not allowed")

    # Convert to Path and resolve
    try:
        path = Path(decoded_path)

        # If relative, resolve against allowed_base
        if not path.is_absolute():
            path = allowed_base / path

        # Resolve to absolute path, following symlinks
        resolved = path.resolve()

    except (OSError, RuntimeError) as e:
        logger.warning(f"Path resolution failed: {e}")
        raise ValueError("Invalid path format")

    # Verify the resolved path is within allowed_base
    try:
        allowed_resolved = allowed_base.resolve()
        resolved.relative_to(allowed_resolved)
    except ValueError:
        logger.warning(
            f"Path escape attempt: {resolved} is outside {allowed_resolved}"
        )
        raise ValueError("Invalid path: access denied")

    # Optionally check existence
    if must_exist and not resolved.exists():
        raise ValueError("Path does not exist")

    return resolved


def validate_identifier(
    value: str,
    name: str = "identifier",
    max_length: int = 100,
    pattern: Optional[re.Pattern] = None
) -> str:
    """
    Validate that a value matches a safe identifier pattern.

    Args:
        value: The value to validate
        name: Name of the field (for error messages)
        max_length: Maximum allowed length
        pattern: Custom regex pattern (defaults to alphanumeric + underscore + hyphen)

    Returns:
        The validated value (unchanged if valid)

    Raises:
        ValueError: If the value is invalid
    """
    if not value:
        raise ValueError(f"{name} cannot be empty")

    if len(value) > max_length:
        raise ValueError(f"{name} exceeds maximum length of {max_length}")

    # Use provided pattern or default safe pattern
    check_pattern = pattern or SAFE_IDENTIFIER_PATTERN

    if not check_pattern.match(value):
        logger.warning(f"Invalid {name} format: {value[:50]}")
        raise ValueError(f"Invalid {name} format")

    return value


def validate_display_name(
    value: str,
    max_length: int = 200,
    default: str = "ATLAS"
) -> str:
    """
    Validate and sanitize a display name for use in configuration files.

    Args:
        value: The display name to validate
        max_length: Maximum allowed length
        default: Default value if input is invalid

    Returns:
        The sanitized display name
    """
    if not value or not value.strip():
        logger.info(f"Empty display name, using default: {default}")
        return default

    # Strip whitespace
    cleaned = value.strip()

    # Truncate if too long
    if len(cleaned) > max_length:
        cleaned = cleaned[:max_length]
        logger.info(f"Display name truncated to {max_length} characters")

    # Check for safe characters
    if not SAFE_DISPLAY_NAME_PATTERN.match(cleaned):
        # Remove unsafe characters
        sanitized = ''.join(
            c for c in cleaned
            if c.isalnum() or c in ' -_.,;:()[]'
        )
        if not sanitized:
            logger.warning(f"Display name contains only unsafe characters, using default")
            return default
        logger.info(f"Display name sanitized: removed unsafe characters")
        cleaned = sanitized

    # Escape characters that could break env file format
    # Replace newlines and carriage returns
    cleaned = cleaned.replace('\n', ' ').replace('\r', ' ')
    # Escape quotes
    cleaned = cleaned.replace('"', '\\"').replace("'", "\\'")

    return cleaned


def validate_github_url(url: str) -> Tuple[str, str, str]:
    """
    Validate a GitHub repository URL and extract components.

    Args:
        url: The repository URL to validate

    Returns:
        Tuple of (host, owner, repo)

    Raises:
        ValueError: If the URL is invalid or not a GitHub URL
    """
    if not url:
        raise ValueError("Repository URL cannot be empty")

    # Remove .git suffix if present
    clean_url = url.rstrip('/')
    if clean_url.endswith('.git'):
        clean_url = clean_url[:-4]

    # Parse URL
    from urllib.parse import urlparse
    parsed = urlparse(clean_url)

    # Validate host
    host = parsed.netloc or parsed.path.split('/')[0]
    if not GITHUB_HOST_PATTERN.match(host):
        logger.warning(f"Non-GitHub URL rejected: {host}")
        raise ValueError("Only GitHub repositories are supported")

    # Extract owner and repo from path
    path_parts = [p for p in parsed.path.split('/') if p and p != host]

    if len(path_parts) < 2:
        raise ValueError("Invalid repository URL: missing owner or repository name")

    owner = path_parts[0]
    repo = path_parts[1]

    # Validate owner and repo names
    validate_identifier(owner, "repository owner", max_length=39)
    validate_identifier(repo, "repository name", max_length=100)

    return host, owner, repo


def validate_repo_subpath(subpath: str) -> str:
    """
    Validate a subdirectory path within a repository.

    Args:
        subpath: The subdirectory path to validate

    Returns:
        The validated path (normalized)

    Raises:
        ValueError: If the path contains traversal attempts
    """
    if not subpath:
        return ""

    # URL decode
    decoded = unquote(subpath)

    # Remove leading slashes
    cleaned = decoded.lstrip('/').lstrip('\\')

    # Check for traversal
    if '..' in cleaned:
        logger.warning(f"Repository subpath traversal attempt: {subpath[:100]}")
        raise ValueError("Invalid repository path: directory traversal not allowed")

    # Normalize path separators
    cleaned = cleaned.replace('\\', '/')

    return cleaned


def validate_regex_pattern(
    pattern: str,
    timeout_seconds: float = 1.0
) -> Tuple[bool, Optional[str], Optional[re.Pattern]]:
    """
    Validate a regex pattern for syntax and potential ReDoS.

    Args:
        pattern: The regex pattern to validate
        timeout_seconds: Maximum time allowed for compilation (not enforced in Python)

    Returns:
        Tuple of (is_valid, error_message, compiled_pattern)
    """
    if not pattern:
        return False, "Pattern cannot be empty", None

    if len(pattern) > 1000:
        return False, "Pattern exceeds maximum length", None

    # Check for potentially catastrophic patterns
    # These are heuristics, not foolproof
    dangerous_patterns = [
        r'\(.*\+\)\+',  # Nested quantifiers like (a+)+
        r'\(.*\*\)\*',  # Nested quantifiers like (a*)*
        r'\(.*\?\)\+',  # Nested quantifiers
        r'(\.\*){3,}',  # Multiple .* in sequence
    ]

    for dangerous in dangerous_patterns:
        if re.search(dangerous, pattern):
            logger.warning(f"Potentially dangerous regex pattern detected")
            return False, "Pattern may cause performance issues", None

    # Try to compile
    try:
        compiled = re.compile(pattern)
        return True, None, compiled
    except re.error as e:
        return False, f"Invalid regex syntax: {str(e)}", None
    except Exception as e:
        logger.error(f"Unexpected error compiling regex: {e}")
        return False, "Failed to validate pattern", None
