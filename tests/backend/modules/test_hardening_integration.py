"""
Integration tests for Cloudflare deployment hardening.

Tests rate limiting, CORS restrictions, and auth mode compatibility
as specified in OpenSpec change: harden-cloudflare-deployment
(tasks 2.6, 3.3, 7.1-7.5).

Uses httpx TestClient against the FastAPI app with mocked backends.
"""

import pytest
import os
import time
from unittest.mock import patch, MagicMock, Mock

# Set required env vars BEFORE importing the app
os.environ.setdefault("ENVIRONMENT", "development")

# We need a .env.development file to exist - check and skip if not
_env_path = os.path.join(os.path.dirname(__file__), "..", "..", "..", "config", ".env.development")
_env_exists = os.path.exists(os.path.normpath(_env_path))


@pytest.fixture
def mock_telemetry():
    """Mock telemetry initialization to avoid Phoenix dependency."""
    with patch("backend.telemetry.core.initialize_telemetry", return_value=True), \
         patch("backend.telemetry.is_telemetry_initialized", return_value=True), \
         patch("backend.telemetry.core._telemetry_initialized", True):
        yield


@pytest.fixture
def mock_config():
    """Mock configuration initialization."""
    with patch("backend.modules.config.initialize_config"):
        yield


@pytest.fixture
def test_client(mock_telemetry, mock_config):
    """Create a test client for the FastAPI app."""
    # Must import after env is set
    from httpx import ASGITransport, AsyncClient
    from backend.app import app
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")


# ============================================================
# Task 2.6: Rate limiting unit tests
# ============================================================


class TestRateLimitKeyFunction:
    """Test the rate limit key extraction logic."""

    def test_cf_connecting_ip_preferred(self):
        """Cf-Connecting-IP header is used when present (Cloudflare proxy)."""
        from backend.rate_limit import _rate_limit_key

        request = MagicMock()
        request.headers.get = lambda h: {
            "Cf-Connecting-IP": "203.0.113.50",
            "X-Forwarded-For": "10.0.0.1, 172.16.0.1",
        }.get(h)
        request.client.host = "127.0.0.1"

        assert _rate_limit_key(request) == "203.0.113.50"

    def test_x_forwarded_for_fallback(self):
        """X-Forwarded-For first IP is used when Cf-Connecting-IP is absent."""
        from backend.rate_limit import _rate_limit_key

        request = MagicMock()
        request.headers.get = lambda h: {
            "X-Forwarded-For": "203.0.113.50, 10.0.0.1",
        }.get(h)
        request.client.host = "127.0.0.1"

        assert _rate_limit_key(request) == "203.0.113.50"

    def test_remote_addr_final_fallback(self):
        """Falls back to request.client.host when no proxy headers."""
        from backend.rate_limit import _rate_limit_key

        request = MagicMock()
        request.headers.get = lambda h: None
        request.client.host = "192.168.1.100"

        assert _rate_limit_key(request) == "192.168.1.100"

    def test_unknown_when_no_client(self):
        """Returns 'unknown' when request.client is None."""
        from backend.rate_limit import _rate_limit_key

        request = MagicMock()
        request.headers.get = lambda h: None
        request.client = None

        assert _rate_limit_key(request) == "unknown"


class TestRateLimitConfig:
    """Test rate limit configuration."""

    def test_default_rate_limit(self):
        """Default rate limit is 60/minute."""
        from backend.rate_limit import RATE_LIMIT_STRING
        # Default or env-configured value
        assert "/minute" in RATE_LIMIT_STRING

    def test_limiter_has_no_default_limits(self):
        """Limiter has no default limits (only applied via decorator)."""
        from backend.rate_limit import limiter
        assert limiter._default_limits == []


# ============================================================
# Task 3.3: CORS restriction verification
# ============================================================


class TestCorsConfiguration:
    """Verify CORS is configured with restricted methods and headers."""

    def test_cors_methods_restricted(self):
        """CORS allows only GET, POST, OPTIONS (not PUT, DELETE, PATCH)."""
        from backend.app import app

        cors_middleware = None
        for middleware in app.user_middleware:
            if hasattr(middleware, 'cls') and middleware.cls.__name__ == 'CORSMiddleware':
                cors_middleware = middleware
                break

        assert cors_middleware is not None, "CORSMiddleware not found"
        allowed_methods = cors_middleware.kwargs.get("allow_methods", [])
        assert "GET" in allowed_methods
        assert "POST" in allowed_methods
        assert "OPTIONS" in allowed_methods
        assert "*" not in allowed_methods
        assert "PUT" not in allowed_methods
        assert "DELETE" not in allowed_methods
        assert "PATCH" not in allowed_methods

    def test_cors_headers_explicit(self):
        """CORS allows only explicitly listed headers."""
        from backend.app import app

        cors_middleware = None
        for middleware in app.user_middleware:
            if hasattr(middleware, 'cls') and middleware.cls.__name__ == 'CORSMiddleware':
                cors_middleware = middleware
                break

        assert cors_middleware is not None
        allowed_headers = cors_middleware.kwargs.get("allow_headers", [])
        assert "*" not in allowed_headers
        assert "Content-Type" in allowed_headers
        assert "Authorization" in allowed_headers
        assert "X-Telemetry-Opt-In" in allowed_headers
        assert "X-Trace-Id" in allowed_headers
        assert "X-Request-Id" in allowed_headers


# ============================================================
# Tasks 7.1-7.3: Auth mode compatibility
# ============================================================


class TestAuthModeCloudflareWithJwt:
    """Task 7.1: Test AUTH_METHOD=cloudflare with JWT validation."""

    def test_cloudflare_auth_with_jwt_configured(self, monkeypatch):
        """When JWT is configured, extract_cloudflare_user requires valid JWT."""
        monkeypatch.setenv("AUTH_METHOD", "cloudflare")
        monkeypatch.setenv("CLOUDFLARE_TEAM_DOMAIN", "test.cloudflareaccess.com")
        monkeypatch.setenv("CLOUDFLARE_ACCESS_AUD", "test-aud")

        from backend.modules.auth import extract_cloudflare_user

        # Request with email header but no JWT - should be rejected
        request = MagicMock()
        request.headers.get = lambda h, default=None: {
            "Cf-Access-Authenticated-User-Email": "user@example.com",
        }.get(h, default)

        result = extract_cloudflare_user(request)
        assert result is None, "Should reject request without JWT when JWT validation is configured"

    def test_cloudflare_auth_without_jwt_configured(self, monkeypatch):
        """When JWT is not configured, falls back to header trust."""
        monkeypatch.setenv("AUTH_METHOD", "cloudflare")
        monkeypatch.setenv("CLOUDFLARE_TEAM_DOMAIN", "")
        monkeypatch.setenv("CLOUDFLARE_ACCESS_AUD", "")

        from backend.modules.auth import extract_cloudflare_user

        request = MagicMock()
        request.headers.get = lambda h, default=None: {
            "Cf-Access-Authenticated-User-Email": "user@example.com",
        }.get(h, default)

        result = extract_cloudflare_user(request)
        assert result is not None
        assert result["email"] == "user@example.com"
        assert result["auth_method"] == "cloudflare"


class TestAuthModeCognitoUnaffected:
    """Task 7.2: Test AUTH_METHOD=cognito is unaffected by hardening changes."""

    def test_cognito_mode_ignores_cloudflare_env(self, monkeypatch):
        """Cognito mode doesn't use Cloudflare JWT validation."""
        monkeypatch.setenv("AUTH_METHOD", "cognito")
        monkeypatch.setenv("CLOUDFLARE_TEAM_DOMAIN", "test.cloudflareaccess.com")
        monkeypatch.setenv("CLOUDFLARE_ACCESS_AUD", "test-aud")

        from backend.modules.auth import get_auth_method
        assert get_auth_method() == "cognito"

    def test_cognito_get_authenticated_user_requires_bearer(self, monkeypatch):
        """Cognito mode still requires Authorization: Bearer header."""
        monkeypatch.setenv("AUTH_METHOD", "cognito")
        monkeypatch.setenv("VITE_COGNITO_REGION", "us-east-1")
        monkeypatch.setenv("VITE_COGNITO_USERPOOL_ID", "us-east-1_test")
        monkeypatch.setenv("VITE_COGNITO_CLIENT_ID", "testclient")

        from backend.modules.auth import get_authenticated_user
        from fastapi import HTTPException

        request = MagicMock()
        request.headers.get = lambda h: None

        with pytest.raises(HTTPException) as exc_info:
            get_authenticated_user(request)
        assert exc_info.value.status_code == 401


class TestAuthModeNoneUnaffected:
    """Task 7.3: Test AUTH_METHOD=none is unaffected by hardening changes."""

    def test_none_mode_returns_anonymous(self, monkeypatch):
        """None mode returns anonymous user regardless of Cloudflare env."""
        monkeypatch.setenv("AUTH_METHOD", "none")
        monkeypatch.setenv("CLOUDFLARE_TEAM_DOMAIN", "test.cloudflareaccess.com")
        monkeypatch.setenv("CLOUDFLARE_ACCESS_AUD", "test-aud")

        from backend.modules.auth import get_authenticated_user

        request = MagicMock()
        result = get_authenticated_user(request)

        assert result["sub"] == "anonymous"
        assert result["authenticated"] is False
        assert result["auth_method"] == "none"

    def test_none_mode_optional_returns_anonymous(self, monkeypatch):
        """optional_authenticated_user in none mode returns anonymous."""
        monkeypatch.setenv("AUTH_METHOD", "none")

        from backend.modules.auth import optional_authenticated_user

        request = MagicMock()
        result = optional_authenticated_user(request)

        assert result["sub"] == "anonymous"
        assert result["authenticated"] is False


# ============================================================
# Task 5: Error message sanitisation verification
# ============================================================


class TestErrorMessageSanitisation:
    """Verify error messages don't leak implementation details."""

    def test_llm_provider_error_generic(self, monkeypatch):
        """LLM provider errors use generic message, not env var names."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "")
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

        from backend.modules.llm import create_llm

        with pytest.raises(ValueError) as exc_info:
            create_llm(provider="ANTHROPIC", model_name="test")

        error_msg = str(exc_info.value)
        assert "ANTHROPIC_API_KEY" not in error_msg
        assert "Contact administrator" in error_msg

    def test_unknown_provider_error_generic(self):
        """Unknown provider error doesn't list supported providers."""
        from backend.modules.llm import create_llm

        with pytest.raises(ValueError) as exc_info:
            create_llm(provider="BADPROVIDER", model_name="test")

        error_msg = str(exc_info.value)
        assert "BADPROVIDER" not in error_msg
        assert "OLLAMA" not in error_msg
        assert "Contact administrator" in error_msg

    def test_missing_provider_error_generic(self, monkeypatch):
        """Missing provider error doesn't mention TEST_TARGET or .env."""
        monkeypatch.delenv("TEST_TARGET", raising=False)

        from backend.modules.llm import create_llm

        # Mock get_llm_config to return empty config so provider is truly None
        with patch("backend.modules.llm.get_llm_config", return_value={"provider": None, "model": None}):
            with pytest.raises(ValueError) as exc_info:
                create_llm()

        error_msg = str(exc_info.value)
        assert "TEST_TARGET" not in error_msg
        assert ".env" not in error_msg
        assert "Contact administrator" in error_msg
