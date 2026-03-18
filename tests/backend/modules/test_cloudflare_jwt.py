"""
Unit tests for Cloudflare Access JWT validation.

Tests the implementation of verify_cloudflare_jwt() and the updated
extract_cloudflare_user() in backend/modules/auth.py, as specified in
OpenSpec change: harden-cloudflare-deployment (task 1.6).

These tests mock the Cloudflare JWKS endpoint and JWT tokens to validate:
- Valid token acceptance
- Expired token rejection
- Wrong audience rejection
- Missing header rejection
- Key rotation fallback (re-fetch on kid mismatch)
- Graceful fallback when JWT validation is not configured
"""

import pytest
import time
import json
from unittest.mock import patch, MagicMock, Mock
from jose import jwt as jose_jwt
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend


# Generate a test RSA key pair for signing JWTs
_test_private_key = rsa.generate_private_key(
    public_exponent=65537,
    key_size=2048,
    backend=default_backend()
)
_test_public_key = _test_private_key.public_key()


def _get_public_key_jwk():
    """Convert the test public key to JWK format for mock JWKS response."""
    from jose.utils import long_to_base64
    public_numbers = _test_public_key.public_numbers()
    return {
        "kty": "RSA",
        "kid": "test-kid-1",
        "use": "sig",
        "alg": "RS256",
        "n": long_to_base64(public_numbers.n).decode("utf-8"),
        "e": long_to_base64(public_numbers.e).decode("utf-8"),
    }


def _make_jwt(claims, kid="test-kid-1"):
    """Sign a JWT with the test private key."""
    private_pem = _test_private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
    )
    return jose_jwt.encode(
        claims,
        private_pem,
        algorithm="RS256",
        headers={"kid": kid}
    )


def _valid_claims(audience="test-aud", team_domain="test.cloudflareaccess.com"):
    """Generate valid JWT claims."""
    now = int(time.time())
    return {
        "aud": [audience],
        "email": "researcher@example.com",
        "sub": "user-uuid-123",
        "iss": f"https://{team_domain}",
        "iat": now - 60,
        "exp": now + 3600,
    }


@pytest.fixture(autouse=True)
def reset_jwks_cache():
    """Reset the Cloudflare JWKS cache between tests."""
    import backend.modules.auth as auth_module
    auth_module._cf_jwks_cache = None
    auth_module._cf_jwks_cache_timestamp = 0
    yield
    auth_module._cf_jwks_cache = None
    auth_module._cf_jwks_cache_timestamp = 0


@pytest.fixture
def cloudflare_env(monkeypatch):
    """Set Cloudflare JWT validation env vars."""
    monkeypatch.setenv("AUTH_METHOD", "cloudflare")
    monkeypatch.setenv("CLOUDFLARE_TEAM_DOMAIN", "test.cloudflareaccess.com")
    monkeypatch.setenv("CLOUDFLARE_ACCESS_AUD", "test-aud")


@pytest.fixture
def mock_jwks_fetch():
    """Mock the HTTP request to fetch Cloudflare JWKS."""
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"keys": [_get_public_key_jwk()]}
    mock_response.raise_for_status = Mock()

    with patch("backend.modules.auth.requests.get", return_value=mock_response) as mock_get:
        yield mock_get


class TestVerifyCloudflareJwt:
    """Unit tests for verify_cloudflare_jwt()."""

    def test_valid_token_accepted(self, cloudflare_env, mock_jwks_fetch):
        """Valid JWT with correct audience and signature is accepted."""
        from backend.modules.auth import verify_cloudflare_jwt

        token = _make_jwt(_valid_claims())
        request = MagicMock()
        request.headers.get = lambda h: token if h == "Cf-Access-Jwt-Assertion" else None

        result = verify_cloudflare_jwt(request)

        assert result is not None
        assert result["email"] == "researcher@example.com"

    def test_expired_token_rejected(self, cloudflare_env, mock_jwks_fetch):
        """Expired JWT is rejected."""
        from backend.modules.auth import verify_cloudflare_jwt

        claims = _valid_claims()
        claims["exp"] = int(time.time()) - 3600  # Expired 1 hour ago
        claims["iat"] = int(time.time()) - 7200
        token = _make_jwt(claims)

        request = MagicMock()
        request.headers.get = lambda h: token if h == "Cf-Access-Jwt-Assertion" else None

        result = verify_cloudflare_jwt(request)
        assert result is None

    def test_wrong_audience_rejected(self, cloudflare_env, mock_jwks_fetch):
        """JWT with wrong audience claim is rejected."""
        from backend.modules.auth import verify_cloudflare_jwt

        claims = _valid_claims(audience="wrong-audience")
        token = _make_jwt(claims)

        request = MagicMock()
        request.headers.get = lambda h: token if h == "Cf-Access-Jwt-Assertion" else None

        result = verify_cloudflare_jwt(request)
        assert result is None

    def test_missing_jwt_header_rejected(self, cloudflare_env, mock_jwks_fetch):
        """Request without Cf-Access-Jwt-Assertion header is rejected."""
        from backend.modules.auth import verify_cloudflare_jwt

        request = MagicMock()
        request.headers.get = lambda h: None

        result = verify_cloudflare_jwt(request)
        assert result is None

    def test_key_rotation_fallback(self, cloudflare_env):
        """On kid mismatch, re-fetches keys once and retries."""
        from backend.modules.auth import verify_cloudflare_jwt

        # First response has old key (wrong kid), second has correct key
        old_key = _get_public_key_jwk()
        old_key["kid"] = "old-kid"
        new_key = _get_public_key_jwk()

        mock_response_old = Mock()
        mock_response_old.status_code = 200
        mock_response_old.json.return_value = {"keys": [old_key]}
        mock_response_old.raise_for_status = Mock()

        mock_response_new = Mock()
        mock_response_new.status_code = 200
        mock_response_new.json.return_value = {"keys": [new_key]}
        mock_response_new.raise_for_status = Mock()

        with patch("backend.modules.auth.requests.get", side_effect=[mock_response_old, mock_response_new]):
            token = _make_jwt(_valid_claims(), kid="test-kid-1")
            request = MagicMock()
            request.headers.get = lambda h: token if h == "Cf-Access-Jwt-Assertion" else None

            result = verify_cloudflare_jwt(request)
            assert result is not None
            assert result["email"] == "researcher@example.com"

    def test_skipped_when_not_configured(self, monkeypatch):
        """Returns None when CLOUDFLARE_TEAM_DOMAIN or CLOUDFLARE_ACCESS_AUD not set."""
        from backend.modules.auth import verify_cloudflare_jwt

        monkeypatch.setenv("CLOUDFLARE_TEAM_DOMAIN", "")
        monkeypatch.setenv("CLOUDFLARE_ACCESS_AUD", "")

        request = MagicMock()
        result = verify_cloudflare_jwt(request)
        assert result is None

    def test_jwks_fetch_failure_returns_none(self, cloudflare_env):
        """Returns None when JWKS endpoint is unreachable."""
        from backend.modules.auth import verify_cloudflare_jwt

        with patch("backend.modules.auth.requests.get", side_effect=Exception("Network error")):
            token = _make_jwt(_valid_claims())
            request = MagicMock()
            request.headers.get = lambda h: token if h == "Cf-Access-Jwt-Assertion" else None

            result = verify_cloudflare_jwt(request)
            assert result is None


class TestExtractCloudflareUserWithJwt:
    """Test extract_cloudflare_user() with JWT validation enabled/disabled."""

    def test_jwt_enabled_uses_email_from_claims(self, cloudflare_env, mock_jwks_fetch):
        """When JWT is configured, email is extracted from validated claims."""
        from backend.modules.auth import extract_cloudflare_user

        token = _make_jwt(_valid_claims())
        request = MagicMock()
        request.headers.get = lambda h: {
            "Cf-Access-Jwt-Assertion": token,
            "Cf-Access-Authenticated-User-Email": "spoofed@evil.com",
        }.get(h)

        result = extract_cloudflare_user(request)
        assert result is not None
        # Email comes from JWT claims, not the spoofable header
        assert result["email"] == "researcher@example.com"
        assert result["sub"] == "researcher@example.com"

    def test_jwt_disabled_falls_back_to_header(self, monkeypatch):
        """When JWT not configured, falls back to header trust."""
        from backend.modules.auth import extract_cloudflare_user

        monkeypatch.setenv("AUTH_METHOD", "cloudflare")
        monkeypatch.setenv("CLOUDFLARE_TEAM_DOMAIN", "")
        monkeypatch.setenv("CLOUDFLARE_ACCESS_AUD", "")

        request = MagicMock()
        request.headers.get = lambda h, default=None: "user@university.edu" if h == "Cf-Access-Authenticated-User-Email" else default

        result = extract_cloudflare_user(request)
        assert result is not None
        assert result["email"] == "user@university.edu"

    def test_jwt_validation_failure_rejects_request(self, cloudflare_env, mock_jwks_fetch):
        """When JWT is configured but invalid, request is rejected even with valid email header."""
        from backend.modules.auth import extract_cloudflare_user

        request = MagicMock()
        request.headers.get = lambda h: {
            "Cf-Access-Jwt-Assertion": "invalid.jwt.token",
            "Cf-Access-Authenticated-User-Email": "user@university.edu",
        }.get(h)

        result = extract_cloudflare_user(request)
        assert result is None
