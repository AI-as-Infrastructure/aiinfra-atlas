"""
Authentication module for ATLAS using AWS Cognito.

This module provides JWT validation and user management for AWS Cognito
when enabled via environment variables.
"""

import os
import logging
import json
import time
from typing import Optional, Dict, Any, List

COGNITO_SESSION_TIMEOUT = 3600  # 1 hour for research sessions
from jose import jwk, jwt
from jose.utils import base64url_decode
import requests
from fastapi import Depends, HTTPException, status
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

def is_cognito_enabled() -> bool:
    """Check if Cognito authentication is enabled via environment variable."""
    return os.getenv("VITE_USE_COGNITO_AUTH", "false").lower() == "true"

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
        response = requests.get(jwks_url)
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
        
        payload = jwt.decode(
            token,
            rsa_key,
            algorithms=["RS256"],
            audience=client_id,
            issuer=f"https://cognito-idp.{region}.amazonaws.com/{user_pool_id}",
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
    except:
        return {"sub": "anonymous", "username": "anonymous", "authenticated": False}
