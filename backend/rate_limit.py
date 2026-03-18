"""
Rate limiting configuration for ATLAS.

Shared limiter instance used by app.py and router modules.
Uses Cf-Connecting-IP behind Cloudflare, falls back to remote address.
"""

import os
from fastapi import Request
from slowapi import Limiter


def _rate_limit_key(request: Request) -> str:
    """Extract client IP for rate limiting, accounting for Cloudflare proxy."""
    cf_ip = request.headers.get("Cf-Connecting-IP")
    if cf_ip:
        return cf_ip.strip()
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


RATE_LIMIT_PER_MINUTE = os.getenv("RATE_LIMIT_PER_MINUTE", "60")
RATE_LIMIT_STRING = f"{RATE_LIMIT_PER_MINUTE}/minute"

limiter = Limiter(key_func=_rate_limit_key, default_limits=[])
