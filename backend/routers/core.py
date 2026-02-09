"""
Core API endpoints for ATLAS.

Includes health checks, configuration, diagnostics, and telemetry status.
"""

import os
import logging
from datetime import datetime
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import JSONResponse

from backend.modules.config import get_config, get_system_prompt, get_corpus_options
from backend.modules.auth import optional_user, verify_cognito_token, is_cognito_enabled
from backend.telemetry import telemetry_initialized

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/")
async def root():
    """Health check endpoint"""
    return {"status": "ok"}


@router.get("/api/health")
def health_check():
    """Health check endpoint"""
    return {"status": "ok"}


@router.get("/api/config")
def get_config_endpoint():
    """Return application configuration for UI display."""
    config = get_config()
    retriever_config = config.get("retriever_config", {})

    # Import the full system prompt from system_prompts
    from backend.modules.system_prompts import system_prompt_text

    # Build configuration for API use
    config_data = {
        "ATLAS_VERSION": config.get("ATLAS_VERSION", "1.0.0"),
        "SYSTEM_PROMPT": get_system_prompt()[:150] + "..." if len(get_system_prompt()) > 150 else get_system_prompt(),
        "FULL_SYSTEM_PROMPT": system_prompt_text,
        "CORPUS_OPTIONS": get_corpus_options(),

        # Include all retriever configuration
        "target_id": retriever_config.get("target_id"),
        "target_version": retriever_config.get("target_version", "1.0"),
        "embedding_model": retriever_config.get("embedding_model"),
        "search_type": retriever_config.get("search_type"),
        "search_k": retriever_config.get("search_k"),
        "search_score_threshold": retriever_config.get("search_score_threshold"),
        "pooling": retriever_config.get("pooling"),
        "citation_limit": retriever_config.get("citation_limit"),
        "LARGE_RETRIEVAL_SIZE_SINGLE_CORPUS": retriever_config.get("LARGE_RETRIEVAL_SIZE_SINGLE_CORPUS"),
        "LARGE_RETRIEVAL_SIZE_ALL_CORPUS": retriever_config.get("LARGE_RETRIEVAL_SIZE_ALL_CORPUS"),
        "algorithm": retriever_config.get("algorithm"),
        "chunk_size": retriever_config.get("chunk_size"),
        "chunk_overlap": retriever_config.get("chunk_overlap"),
        "text_splitter_type": retriever_config.get("text_splitter_type"),
        "index_name": retriever_config.get("index_name"),

        # Include LLM configuration
        "llm_provider": config.get("llm_provider"),
        "llm_model": config.get("llm_model"),

        # Include vector database info
        "composite_target": f"{retriever_config.get('target_id')}_{retriever_config.get('chroma_collection_name')}"
    }

    # Add extra config fields from environment variables
    config_data["MULTI_CORPUS_VECTORSTORE"] = os.getenv("MULTI_CORPUS_VECTORSTORE")
    config_data["CHROMA_COLLECTION_NAME"] = os.getenv("CHROMA_COLLECTION_NAME")

    return JSONResponse(content=config_data)


@router.get("/api/telemetry")
def telemetry_status():
    """Return the status of telemetry (initialized or not) for health checks."""
    return {"telemetry_initialized": telemetry_initialized}


@router.get("/api/diagnostics")
async def diagnostics(request: Request):
    """Return diagnostic information to help debug issues."""
    # Check if authentication is required based on environment
    auth_required = os.getenv("VITE_USE_COGNITO_AUTH", "false").lower() == "true"

    if auth_required:
        # Get the authorization header
        auth_header = request.headers.get("Authorization")
        if not auth_header:
            raise HTTPException(
                status_code=401,
                detail="Authentication required for diagnostics"
            )

        # Verify user is authenticated
        user = await optional_user(request)
        if not user.get("authenticated", False):
            raise HTTPException(
                status_code=403,
                detail="Unauthorized access to diagnostics"
            )

    # Get basic config info - only non-sensitive information
    config_info = {}
    try:
        config = get_config()
        retriever_config = config.get("retriever_config", {})
        config_info = {
            "target_id": retriever_config.get("target_id"),
            "llm_provider": config.get("llm_provider"),
            "llm_model": config.get("llm_model"),
            "embedding_model": retriever_config.get("embedding_model"),
            "citation_limit": retriever_config.get("citation_limit"),
            "large_retrieval_size": retriever_config.get("large_retrieval_size"),
        }
    except Exception:
        config_info = {"error": "Configuration error occurred"}

    # Check critical environment variables - only return presence, not values
    env_vars = {
        "TEST_TARGET": bool(os.getenv("TEST_TARGET")),
        "REDIS_HOST": bool(os.getenv("REDIS_HOST")),
        "REDIS_PORT": bool(os.getenv("REDIS_PORT")),
        "REDIS_PASSWORD": bool(os.getenv("REDIS_PASSWORD")),
        "PHOENIX_API_KEY": bool(os.getenv("PHOENIX_API_KEY")),
        "ANTHROPIC_API_KEY": bool(os.getenv("ANTHROPIC_API_KEY")),
        "OPENAI_API_KEY": bool(os.getenv("OPENAI_API_KEY")),
    }

    return {
        "environment": env_vars,
        "config": config_info,
        "telemetry_initialized": telemetry_initialized
    }


@router.get("/api/debug/user-id")
def debug_user_id_extraction(request: Request):
    """Debug endpoint to verify user ID extraction is working correctly."""
    from backend.services.anonymous_id_service import anonymous_id_service

    # Get system configuration for inter-rater status
    from backend.modules.system_configuration import get_system_config
    system_config = get_system_config()

    result = {
        "timestamp": datetime.now().isoformat(),
        "environment": os.getenv("ENVIRONMENT", "unknown"),
        "cognito_settings": {
            "VITE_USE_COGNITO_AUTH": os.getenv("VITE_USE_COGNITO_AUTH", "false"),
            "cognito_enabled": is_cognito_enabled(),
            "inter_rater_enabled": str(system_config.is_inter_rater_enabled()).lower(),
        },
        "anonymous_id_service": anonymous_id_service.validate_environment_isolation()
    }

    # Try to extract user ID from current request
    try:
        auth_header = request.headers.get("Authorization")
        if auth_header:
            token = auth_header.split(" ", 1)[1] if " " in auth_header else auth_header
            payload = verify_cognito_token(token)

            if payload and payload.get("sub"):
                cognito_sub = payload.get("sub")
                user = {"sub": cognito_sub, "authenticated": True}
                anon_user_id = anonymous_id_service.get_anonymous_id_from_user_data(user)

                result["extraction_result"] = {
                    "success": True,
                    "cognito_sub_prefix": cognito_sub[:8] + "..." if len(cognito_sub) > 8 else cognito_sub,
                    "anonymous_id_format": anon_user_id[:12] + "..." if anon_user_id else None,
                    "anonymous_id_length": len(anon_user_id) if anon_user_id else 0
                }
            else:
                result["extraction_result"] = {
                    "success": False,
                    "error": "Token verified but no 'sub' in payload",
                    "payload_keys": list(payload.keys()) if payload else []
                }
        else:
            result["extraction_result"] = {
                "success": False,
                "error": "No Authorization header present",
                "headers_present": list(request.headers.keys())
            }

    except Exception as e:
        result["extraction_result"] = {
            "success": False,
            "error": f"Exception during extraction: {str(e)}",
            "exception_type": type(e).__name__
        }

    return JSONResponse(content=result)
