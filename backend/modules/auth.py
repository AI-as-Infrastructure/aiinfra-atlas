"""
Authentication module for ATLAS.

Supports three modes selected by AUTH_METHOD environment variable:
- cognito: AWS Cognito JWT validation
- cloudflare: Cloudflare Access header-based identity
- none: No authentication (anonymous users)

Backward compatible with deprecated VITE_USE_COGNITO_AUTH toggle.
"""

import os
import logging
import json
import re
import time
from typing import Optional, Dict, Any, List

COGNITO_SESSION_TIMEOUT = 3600  # 1 hour for research sessions
from jose import jwk, jwt
from jose.utils import base64url_decode
import requests
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# JWT validation setup
security = HTTPBearer(auto_error=False)

# Cache for Cognito JWKS
_jwks_cache = None
_jwks_cache_timestamp = 0
_JWKS_CACHE_TTL = 3600  # Cache JWKs for 1 hour

# Track whether deprecation warning has been logged
_deprecation_warned = False


def get_auth_method() -> str:
    """
    Determine the active authentication method.

    Priority:
    1. AUTH_METHOD env var (canonical)
    2. VITE_USE_COGNITO_AUTH env var (deprecated, with warning)
    3. Default: 'none'
    """
    global _deprecation_warned

    auth_method = os.getenv("AUTH_METHOD", "").strip().lower()
    if auth_method in ("cognito", "cloudflare", "none"):
        return auth_method

    # If AUTH_METHOD is set to an invalid value, fail fast
    if auth_method:
        logger.error(
            f"Invalid AUTH_METHOD='{auth_method}'. "
            "Must be one of: cognito, cloudflare, none"
        )
        raise ValueError(
            f"Invalid AUTH_METHOD='{auth_method}'. "
            "Must be one of: cognito, cloudflare, none"
        )

    # Backward compatibility: map deprecated VITE_USE_COGNITO_AUTH
    legacy_value = os.getenv("VITE_USE_COGNITO_AUTH", "").strip().lower()
    if legacy_value:
        if not _deprecation_warned:
            logger.warning(
                "DEPRECATED: VITE_USE_COGNITO_AUTH is deprecated. "
                "Use AUTH_METHOD=cognito|cloudflare|none instead."
            )
            _deprecation_warned = True
        if legacy_value == "true":
            return "cognito"
        return "none"

    return "none"


def is_cognito_enabled() -> bool:
    """Check if Cognito authentication is enabled. Delegates to get_auth_method()."""
    return get_auth_method() == "cognito"


def get_cognito_config() -> Dict[str, str]:
    """Get Cognito configuration from environment variables."""
    return {
        "region": os.getenv("VITE_COGNITO_REGION", ""),
        "user_pool_id": os.getenv("VITE_COGNITO_USERPOOL_ID", ""),
        "client_id": os.getenv("VITE_COGNITO_CLIENT_ID", ""),
        "domain": os.getenv("VITE_COGNITO_DOMAIN", ""),
        "redirect_uri": os.getenv("VITE_COGNITO_REDIRECT_URI", ""),
        "logout_url": os.getenv("VITE_COGNITO_LOGOUT_URL", ""),
        "oauth_scope": os.getenv("VITE_COGNITO_OAUTH_SCOPE", "")
    }


def get_cognito_jwks():
    """Get Cognito JSON Web Key Set (JWKS) with caching."""
    global _jwks_cache, _jwks_cache_timestamp

    # Return cached JWKS if valid
    current_time = time.time()
    if _jwks_cache and (current_time - _jwks_cache_timestamp) < _JWKS_CACHE_TTL:
        return _jwks_cache

    # Get fresh JWKS
    cognito_config = get_cognito_config()
    region = cognito_config.get("region")
    user_pool_id = cognito_config.get("user_pool_id")

    if not region or not user_pool_id:
        logger.error("Missing Cognito configuration (region or user_pool_id)")
        return None

    try:
        jwks_url = f"https://cognito-idp.{region}.amazonaws.com/{user_pool_id}/.well-known/jwks.json"
        response = requests.get(jwks_url, timeout=10)
        response.raise_for_status()
        _jwks_cache = response.json()
        _jwks_cache_timestamp = current_time
        return _jwks_cache
    except Exception as e:
        logger.error(f"Error getting Cognito JWKS: {e}")
        return None


def verify_cognito_token(token: str) -> Optional[Dict[str, Any]]:
    """Verify a Cognito JWT token and return the claims if valid."""
    if not is_cognito_enabled():
        logger.debug("Cognito auth is disabled, skipping token validation")
        return None

    try:
        # Get the key id (kid) from the token header
        header = jwt.get_unverified_header(token)
        kid = header.get("kid")

        # Get the JWKS
        jwks = get_cognito_jwks()
        if not jwks:
            logger.error("Unable to get JWKS for token validation")
            return None

        # Find the matching key
        rsa_key = None
        for key in jwks.get("keys", []):
            if key.get("kid") == kid:
                rsa_key = key
                break

        if not rsa_key:
            logger.error(f"No matching key found for kid: {kid}")
            return None

        # Verify the token
        cognito_config = get_cognito_config()
        region = cognito_config.get("region")
        user_pool_id = cognito_config.get("user_pool_id")
        client_id = cognito_config.get("client_id")

        # Decode without at_hash verification since we don't pass the access_token here.
        payload = jwt.decode(
            token,
            rsa_key,
            algorithms=["RS256"],
            audience=client_id,
            issuer=f"https://cognito-idp.{region}.amazonaws.com/{user_pool_id}",
            options={"verify_at_hash": False}
        )

        # Check token expiration
        if 'exp' in payload:
            exp_time = payload['exp']
            current_time = time.time()
            if current_time > exp_time:
                logger.warning("Token expired")
                return None

        return payload
    except Exception as e:
        logger.error(f"Error verifying token: {e}")
        return None


_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

def extract_cloudflare_user(request: Request) -> Optional[Dict[str, Any]]:
    """
    Extract user identity from Cloudflare Access headers.

    Cloudflare Access sets Cf-Access-Authenticated-User-Email on every request
    that passes through an Access policy. This header is trusted because traffic
    only reaches the origin through the tunnel.

    Validates email format and length to reject malformed or oversized values.
    """
    email = request.headers.get("Cf-Access-Authenticated-User-Email")
    if not email:
        return None

    email = email.strip()

    # Validate length (RFC 5321: max 254 chars; reject suspiciously short values)
    if len(email) < 5 or len(email) > 254:
        logger.warning(f"Cloudflare email header rejected: invalid length ({len(email)} chars)")
        return None

    # Validate email format
    if not _EMAIL_RE.match(email):
        logger.warning("Cloudflare email header rejected: invalid email format")
        return None

    return {
        "sub": email,
        "username": email,
        "email": email,
        "groups": [],
        "authenticated": True,
        "auth_method": "cloudflare"
    }


def get_authenticated_user(request: Request) -> Dict[str, Any]:
    """
    Unified authentication dispatcher. Returns user dict or raises HTTPException.

    Dispatches to the correct extraction logic based on AUTH_METHOD:
    - cognito: Validates JWT from Authorization header
    - cloudflare: Extracts Cf-Access-Authenticated-User-Email header
    - none: Returns anonymous user
    """
    auth_method = get_auth_method()

    if auth_method == "cognito":
        auth_header = request.headers.get("Authorization")
        if not auth_header:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Not authenticated",
                headers={"WWW-Authenticate": "Bearer"},
            )
        token = auth_header.split(" ", 1)[1] if " " in auth_header else auth_header
        payload = verify_cognito_token(token)
        if not payload:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return {
            "sub": payload.get("sub"),
            "username": payload.get("username", payload.get("email", "unknown")),
            "email": payload.get("email"),
            "groups": payload.get("cognito:groups", []),
            "authenticated": True,
            "auth_method": "cognito"
        }

    elif auth_method == "cloudflare":
        user = extract_cloudflare_user(request)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing Cloudflare Access identity header",
            )
        return user

    else:  # none
        return {
            "sub": "anonymous",
            "username": "anonymous",
            "authenticated": False,
            "auth_method": "none"
        }


def optional_authenticated_user(request: Request) -> Dict[str, Any]:
    """
    Non-throwing authentication dispatcher. Returns anonymous user on failure.
    """
    auth_method = get_auth_method()

    try:
        if auth_method == "cognito":
            auth_header = request.headers.get("Authorization")
            if not auth_header:
                return {"sub": "anonymous", "username": "anonymous", "authenticated": False, "auth_method": "cognito"}
            token = auth_header.split(" ", 1)[1] if " " in auth_header else auth_header
            payload = verify_cognito_token(token)
            if not payload:
                return {"sub": "anonymous", "username": "anonymous", "authenticated": False, "auth_method": "cognito"}
            return {
                "sub": payload.get("sub"),
                "username": payload.get("username", payload.get("email", "unknown")),
                "email": payload.get("email"),
                "groups": payload.get("cognito:groups", []),
                "authenticated": True,
                "auth_method": "cognito"
            }

        elif auth_method == "cloudflare":
            user = extract_cloudflare_user(request)
            if user:
                return user
            return {"sub": "anonymous", "username": "anonymous", "authenticated": False, "auth_method": "cloudflare"}

        else:  # none
            return {"sub": "anonymous", "username": "anonymous", "authenticated": False, "auth_method": "none"}

    except Exception as e:
        logger.error(f"Authentication error in optional_authenticated_user: {type(e).__name__}")
        return {"sub": "anonymous", "username": "anonymous", "authenticated": False, "auth_method": auth_method}


# --- Legacy FastAPI dependency functions (kept for backward compatibility) ---

async def get_current_user(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)):
    """FastAPI dependency for getting the current user from a JWT token."""
    if not is_cognito_enabled():
        # If Cognito is disabled, return a default user
        return {"sub": "anonymous", "username": "anonymous", "authenticated": False}

    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials
    payload = verify_cognito_token(token)

    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return {
        "sub": payload.get("sub"),
        "username": payload.get("username", payload.get("email", "unknown")),
        "email": payload.get("email"),
        "groups": payload.get("cognito:groups", []),
        "authenticated": True
    }

async def optional_user(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)):
    """FastAPI dependency for optional authentication, won't throw an exception."""
    if not is_cognito_enabled():
        return {"sub": "anonymous", "username": "anonymous", "authenticated": False}

    if not credentials:
        return {"sub": "anonymous", "username": "anonymous", "authenticated": False}

    try:
        token = credentials.credentials
        payload = verify_cognito_token(token)

        if not payload:
            return {"sub": "anonymous", "username": "anonymous", "authenticated": False}

        return {
            "sub": payload.get("sub"),
            "username": payload.get("username", payload.get("email", "unknown")),
            "email": payload.get("email"),
            "groups": payload.get("cognito:groups", []),
            "authenticated": True
        }
    except Exception as e:
        logger.error(f"Authentication error in optional_user: {e}")
        return {"sub": "anonymous", "username": "anonymous", "authenticated": False}
