"""
ATLAS Backend Application.

FastAPI application entry point with router configuration.
Endpoints are organized into router modules under backend/routers/.
"""

import os
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from dotenv import load_dotenv
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Reduce httpx logging to avoid exposing URLs in logs
logging.getLogger("httpx").setLevel(logging.WARNING)

# Load environment variables with strict mode
project_root = os.path.dirname(os.path.dirname(__file__))

atlas_environment = os.getenv("ENVIRONMENT")
if not atlas_environment:
    logger.error("ENVIRONMENT variable is not set. Cannot determine which configuration to use.")
    raise EnvironmentError("ENVIRONMENT must be set (e.g., 'development', 'staging', 'production') in your .env file")

env_file_name = f".env.{atlas_environment.lower()}"
env_path = os.path.join(project_root, "config", env_file_name)

if not os.path.exists(env_path):
    logger.error(f"Required environment file not found: {env_path} (ATLAS_ENV='{atlas_environment}')")
    raise FileNotFoundError(f"Cannot find environment file: {env_path}. Deployment is misconfigured.")

logger.info(f"Loading environment variables from: {env_path} (ATLAS_ENV='{atlas_environment}')")
load_dotenv(dotenv_path=env_path, override=True)

# Initialize telemetry after environment variables are loaded
from backend.telemetry.core import initialize_telemetry
from backend.telemetry import telemetry_initialized, telemetry_router

environment = os.getenv("ENVIRONMENT", "development").lower()
telemetry_enabled = os.getenv("TELEMETRY_ENABLED", "true").lower() in ["true", "1", "yes"]

if not telemetry_enabled:
    logger.info("Telemetry disabled via TELEMETRY_ENABLED=false")
    telemetry_success = True
else:
    try:
        telemetry_success = initialize_telemetry()
        if telemetry_success:
            logger.info("Telemetry initialized successfully")
        else:
            logger.error(f"CRITICAL: Telemetry initialization failed in {environment}")
            raise RuntimeError(f"Telemetry is enabled but initialization returned False")
    except Exception as e:
        logger.error(f"CRITICAL: Telemetry initialization failed in {environment}: {e}")
        raise RuntimeError(f"Telemetry initialization failed: {e}")

if not telemetry_initialized:
    if not telemetry_enabled:
        logger.info("Telemetry not initialized (explicitly disabled)")
    else:
        raise RuntimeError(f"Telemetry is enabled but not initialized. The app cannot start without telemetry.")

# Import routers
from backend.routers import (
    core_router,
    query_router,
    feedback_router,
    validation_router,
    cache_router,
    queue_router,
    inter_rater_router,
    retriever_router,
)

# Import configuration initialization
from backend.modules.config import initialize_config

# Initialize FastAPI app
app = FastAPI(title="ATLAS")

# Configure CORS
cors_origins_env = os.environ.get("CORS_ORIGINS", "")
origins = [origin.strip() for origin in cors_origins_env.split(",") if origin.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Telemetry middleware
@app.middleware("http")
async def telemetry_middleware(request: Request, call_next):
    """Middleware to set user telemetry preference based on request headers."""
    from backend.telemetry import set_user_telemetry_preference

    user_enabled = set_user_telemetry_preference(request)

    if request.url.path.startswith("/api/"):
        logger.info(f"Telemetry middleware: User telemetry {'enabled' if user_enabled else 'disabled'} for {request.url.path}")

    response = await call_next(request)
    return response


# Security middleware
@app.middleware("http")
async def security_middleware(request: Request, call_next):
    """Basic security middleware for research prototype"""
    max_size = 10 * 1024 * 1024  # 10MB limit
    content_length = request.headers.get("content-length")
    if content_length and int(content_length) > max_size:
        return JSONResponse(
            status_code=413,
            content={"error": "Request too large", "max_size": f"{max_size // (1024*1024)}MB"}
        )
    response = await call_next(request)
    return response


# HTTPS proxy middleware
@app.middleware("http")
async def handle_forwarded_proto(request: Request, call_next):
    """
    Process the X-Forwarded-Proto header to detect HTTPS correctly.
    """
    forwarded_proto = request.headers.get("X-Forwarded-Proto")
    if forwarded_proto:
        request.scope["scheme"] = forwarded_proto

    response = await call_next(request)
    return response


# Include telemetry router
app.include_router(telemetry_router)

# Include API routers
app.include_router(core_router)
app.include_router(query_router)
app.include_router(feedback_router)
app.include_router(validation_router)
app.include_router(cache_router)
app.include_router(queue_router)
app.include_router(inter_rater_router)
app.include_router(retriever_router)

# Initialize configuration
try:
    logger.info("Initializing configuration and retriever")
    initialize_config()
    logger.info("Configuration and retriever initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize configuration: {e}")
    raise

# Configure TrustedHostMiddleware
cors_origins = os.getenv("CORS_ORIGINS", "localhost,127.0.0.1")
allowed_hosts = [host.strip() for host in cors_origins.split(",")]
allowed_hosts = [host.replace("https://", "").replace("http://", "") for host in allowed_hosts]

if "localhost" not in allowed_hosts:
    allowed_hosts.append("localhost")
if "127.0.0.1" not in allowed_hosts:
    allowed_hosts.append("127.0.0.1")

print(f"TrustedHostMiddleware: Allowing hosts {allowed_hosts}")

app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=allowed_hosts
)

# Static file serving for Cloudflare Tunnel deployment (no nginx).
# Enabled via SERVE_STATIC=true in the systemd service environment.
# Must be mounted AFTER all API routers so /api routes take priority.
if os.getenv("SERVE_STATIC", "").lower() in ("true", "1", "yes"):
    from fastapi.staticfiles import StaticFiles
    from fastapi.responses import FileResponse

    static_dir = os.path.join(project_root, "frontend", "dist")
    if os.path.isdir(static_dir):
        # Serve static assets (JS, CSS, images) from frontend/dist/assets/
        assets_dir = os.path.join(static_dir, "assets")
        if os.path.isdir(assets_dir):
            app.mount("/assets", StaticFiles(directory=assets_dir), name="static-assets")

        # SPA fallback: return index.html for non-API, non-static routes
        @app.get("/{full_path:path}")
        async def spa_fallback(full_path: str):
            """Serve index.html for SPA routing (Vue Router history mode)."""
            file_path = os.path.join(static_dir, full_path)
            if os.path.isfile(file_path):
                return FileResponse(file_path)
            return FileResponse(os.path.join(static_dir, "index.html"))

        logger.info(f"Static file serving enabled from {static_dir}")
    else:
        logger.warning(f"SERVE_STATIC=true but {static_dir} not found. Run frontend build first.")

# Entrypoint for running with Uvicorn
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.app:app", host="0.0.0.0", port=8000, reload=True)
