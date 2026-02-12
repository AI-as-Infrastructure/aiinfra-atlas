"""
Unit tests for path_validator.py security utilities.

Tests cover:
- Path traversal prevention
- URL-encoded traversal attempts
- Identifier validation
- Display name sanitization (including injection attacks)
- GitHub URL validation
- Regex pattern validation
"""

import pytest
import re
from pathlib import Path
from unittest.mock import patch
import tempfile
import os

from backend.modules.path_validator import (
    validate_safe_path,
    validate_identifier,
    validate_display_name,
    validate_github_url,
    validate_repo_subpath,
    validate_regex_pattern,
    SAFE_IDENTIFIER_PATTERN,
    SAFE_DISPLAY_NAME_PATTERN,
)


class TestValidateSafePath:
    """Tests for validate_safe_path function."""

    @pytest.fixture
    def temp_base_dir(self):
        """Create a temporary directory for testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            # Create some subdirectories for testing
            (base / "allowed").mkdir()
            (base / "allowed" / "subdir").mkdir()
            (base / "allowed" / "file.txt").touch()
            yield base

    def test_valid_relative_path(self, temp_base_dir):
        """Valid relative path within allowed base should succeed."""
        result = validate_safe_path("allowed/subdir", temp_base_dir)
        assert result == (temp_base_dir / "allowed" / "subdir").resolve()

    def test_valid_absolute_path_within_base(self, temp_base_dir):
        """Absolute path within allowed base should succeed."""
        allowed_path = temp_base_dir / "allowed"
        result = validate_safe_path(str(allowed_path), temp_base_dir)
        assert result == allowed_path.resolve()

    def test_empty_path_raises(self, temp_base_dir):
        """Empty path should raise ValueError."""
        with pytest.raises(ValueError, match="cannot be empty"):
            validate_safe_path("", temp_base_dir)

    def test_simple_traversal_blocked(self, temp_base_dir):
        """Simple .. traversal should be blocked."""
        with pytest.raises(ValueError, match="directory traversal not allowed"):
            validate_safe_path("../secret", temp_base_dir)

    def test_embedded_traversal_blocked(self, temp_base_dir):
        """Traversal embedded in path should be blocked."""
        with pytest.raises(ValueError, match="directory traversal not allowed"):
            validate_safe_path("allowed/../../../etc/passwd", temp_base_dir)

    def test_url_encoded_traversal_blocked(self, temp_base_dir):
        """URL-encoded .. (%2e%2e) traversal should be blocked."""
        with pytest.raises(ValueError, match="directory traversal not allowed"):
            validate_safe_path("%2e%2e/secret", temp_base_dir)

    def test_mixed_url_encoded_traversal_blocked(self, temp_base_dir):
        """Mixed URL-encoded traversal (.%2e or %2e.) should be blocked."""
        with pytest.raises(ValueError, match="directory traversal not allowed"):
            validate_safe_path(".%2e/secret", temp_base_dir)
        with pytest.raises(ValueError, match="directory traversal not allowed"):
            validate_safe_path("%2e./secret", temp_base_dir)

    def test_double_encoded_traversal_blocked(self, temp_base_dir):
        """Double-encoded traversal attempts should be blocked."""
        # %252e%252e decodes to %2e%2e on first decode
        # After unquote, this becomes ..
        with pytest.raises(ValueError):
            validate_safe_path("%252e%252e/secret", temp_base_dir)

    def test_absolute_path_escape_blocked(self, temp_base_dir):
        """Absolute path outside base should be blocked."""
        with pytest.raises(ValueError, match="access denied"):
            validate_safe_path("/etc/passwd", temp_base_dir)

    def test_null_byte_handling(self, temp_base_dir):
        """Null bytes in path should be handled safely."""
        with pytest.raises(ValueError):
            validate_safe_path("allowed\x00/../secret", temp_base_dir)

    def test_must_exist_with_existing_path(self, temp_base_dir):
        """Path that exists should succeed with must_exist=True."""
        result = validate_safe_path(
            "allowed/file.txt", temp_base_dir, must_exist=True
        )
        assert result.exists()

    def test_must_exist_with_nonexistent_path(self, temp_base_dir):
        """Path that doesn't exist should fail with must_exist=True."""
        with pytest.raises(ValueError, match="does not exist"):
            validate_safe_path(
                "allowed/nonexistent.txt", temp_base_dir, must_exist=True
            )

    def test_backslash_traversal_blocked(self, temp_base_dir):
        """Backslash traversal attempts should be handled."""
        with pytest.raises(ValueError, match="directory traversal not allowed"):
            validate_safe_path("allowed\\..\\..\\secret", temp_base_dir)


class TestValidateIdentifier:
    """Tests for validate_identifier function."""

    def test_valid_identifier(self):
        """Valid alphanumeric identifier should pass."""
        result = validate_identifier("valid_identifier-123")
        assert result == "valid_identifier-123"

    def test_empty_identifier_raises(self):
        """Empty identifier should raise ValueError."""
        with pytest.raises(ValueError, match="cannot be empty"):
            validate_identifier("")

    def test_identifier_with_spaces_fails(self):
        """Identifier with spaces should fail default pattern."""
        with pytest.raises(ValueError, match="Invalid"):
            validate_identifier("has spaces")

    def test_identifier_with_special_chars_fails(self):
        """Identifier with special characters should fail."""
        with pytest.raises(ValueError, match="Invalid"):
            validate_identifier("has@special#chars")

    def test_identifier_too_long_fails(self):
        """Identifier exceeding max length should fail."""
        with pytest.raises(ValueError, match="exceeds maximum length"):
            validate_identifier("a" * 101, max_length=100)

    def test_custom_pattern_accepted(self):
        """Custom pattern should be used when provided."""
        # Allow dots in identifier with custom pattern
        custom_pattern = re.compile(r'^[a-zA-Z0-9._-]+$')
        result = validate_identifier("my.valid.id", pattern=custom_pattern)
        assert result == "my.valid.id"

    def test_custom_name_in_error(self):
        """Custom name should appear in error message."""
        with pytest.raises(ValueError, match="target_id"):
            validate_identifier("bad@id", name="target_id")


class TestValidateDisplayName:
    """Tests for validate_display_name function (injection prevention)."""

    def test_valid_display_name(self):
        """Valid display name should pass unchanged."""
        result = validate_display_name("My Test Project (2024)")
        assert result == "My Test Project (2024)"

    def test_empty_display_name_returns_default(self):
        """Empty display name should return default."""
        result = validate_display_name("")
        assert result == "ATLAS"

    def test_whitespace_only_returns_default(self):
        """Whitespace-only display name should return default."""
        result = validate_display_name("   ")
        assert result == "ATLAS"

    def test_custom_default_used(self):
        """Custom default should be used for empty input."""
        result = validate_display_name("", default="My Default")
        assert result == "My Default"

    def test_truncation_at_max_length(self):
        """Display name exceeding max length should be truncated."""
        long_name = "A" * 300
        result = validate_display_name(long_name, max_length=200)
        assert len(result) == 200

    def test_newline_injection_prevented(self):
        """Newlines in display name should be removed or replaced."""
        result = validate_display_name("Name\nNEW_VAR=malicious")
        # Newline should not be in final result (removed or replaced)
        assert "\n" not in result
        # The = sign is not in the safe pattern, so it will be stripped
        assert "=" not in result

    def test_carriage_return_injection_prevented(self):
        """Carriage returns should be replaced with spaces."""
        result = validate_display_name("Name\rNEW_VAR=malicious")
        assert "\r" not in result

    def test_quote_injection_escaped(self):
        """Quotes should be escaped to prevent env file injection."""
        result = validate_display_name('Name"; export EVIL=1; #')
        # Quotes should be escaped
        assert '";' not in result or '\\"' in result

    def test_single_quote_injection_escaped(self):
        """Single quotes should be escaped."""
        result = validate_display_name("Name'; export EVIL=1; #")
        assert "'" not in result or "\\'" in result

    def test_shell_metacharacters_removed(self):
        """Shell metacharacters should be removed or sanitized."""
        dangerous_inputs = [
            "$(whoami)",
            "`id`",
            "${PATH}",
            "| cat /etc/passwd",
            "& malicious",
            "> /etc/crontab",
            "< /etc/shadow",
        ]
        for dangerous in dangerous_inputs:
            result = validate_display_name(f"Name {dangerous}")
            # Result should not contain shell-dangerous characters
            assert "$" not in result or result.count("$") == 0
            assert "`" not in result
            assert "|" not in result
            assert "&" not in result
            assert ">" not in result
            assert "<" not in result

        # Note: semicolons are allowed in the safe display name pattern
        # since they're commonly used in titles like "Title: Subtitle; More"
        # The SAFE_DISPLAY_NAME_PATTERN includes semicolons as safe

    def test_all_unsafe_chars_returns_default(self):
        """Input with only unsafe characters should return default."""
        result = validate_display_name("$$$```<<<>>>")
        assert result == "ATLAS"

    def test_env_file_format_injection_prevented(self):
        """Complex env file injection attempts should be prevented."""
        # Attempt to inject a new environment variable
        injection = 'Valid Name"\nSECRET_KEY="stolen'
        result = validate_display_name(injection)
        # Should not contain newline
        assert "\n" not in result
        # Should escape or remove quotes
        assert result.count('"') == 0 or '\\"' in result


class TestValidateGithubUrl:
    """Tests for validate_github_url function."""

    def test_valid_https_url(self):
        """Valid HTTPS GitHub URL should parse correctly."""
        host, owner, repo = validate_github_url("https://github.com/owner/repo")
        assert host == "github.com"
        assert owner == "owner"
        assert repo == "repo"

    def test_valid_url_with_git_suffix(self):
        """URL ending with .git should be handled."""
        host, owner, repo = validate_github_url("https://github.com/owner/repo.git")
        assert owner == "owner"
        assert repo == "repo"

    def test_www_github_accepted(self):
        """www.github.com should be accepted."""
        host, owner, repo = validate_github_url("https://www.github.com/owner/repo")
        assert "github.com" in host.lower()

    def test_empty_url_raises(self):
        """Empty URL should raise ValueError."""
        with pytest.raises(ValueError, match="cannot be empty"):
            validate_github_url("")

    def test_non_github_host_rejected(self):
        """Non-GitHub hosts should be rejected."""
        with pytest.raises(ValueError, match="Only GitHub"):
            validate_github_url("https://gitlab.com/owner/repo")

    def test_malformed_url_rejected(self):
        """Malformed URLs should be rejected."""
        with pytest.raises(ValueError):
            validate_github_url("not-a-url")

    def test_url_without_repo_rejected(self):
        """URL without repository name should be rejected."""
        with pytest.raises(ValueError, match="missing owner or repository"):
            validate_github_url("https://github.com/owner")

    def test_invalid_owner_name_rejected(self):
        """Owner name with invalid characters should be rejected."""
        with pytest.raises(ValueError, match="Invalid"):
            validate_github_url("https://github.com/bad@owner/repo")

    def test_invalid_repo_name_rejected(self):
        """Repository name with invalid characters should be rejected."""
        # URL fragments (#) are stripped by urlparse, so use a different invalid char
        with pytest.raises(ValueError, match="Invalid"):
            validate_github_url("https://github.com/owner/bad@repo")


class TestValidateRepoSubpath:
    """Tests for validate_repo_subpath function."""

    def test_valid_subpath(self):
        """Valid subpath should be returned normalized."""
        result = validate_repo_subpath("docs/corpus")
        assert result == "docs/corpus"

    def test_empty_subpath_returns_empty(self):
        """Empty subpath should return empty string."""
        result = validate_repo_subpath("")
        assert result == ""

    def test_leading_slash_removed(self):
        """Leading slashes should be removed."""
        result = validate_repo_subpath("/docs/corpus")
        assert result == "docs/corpus"

    def test_traversal_blocked(self):
        """Directory traversal should be blocked."""
        with pytest.raises(ValueError, match="directory traversal not allowed"):
            validate_repo_subpath("docs/../../../etc/passwd")

    def test_url_encoded_traversal_blocked(self):
        """URL-encoded traversal should be blocked after decoding."""
        with pytest.raises(ValueError, match="directory traversal not allowed"):
            validate_repo_subpath("docs/%2e%2e/secret")

    def test_backslash_normalized(self):
        """Backslashes should be normalized to forward slashes."""
        result = validate_repo_subpath("docs\\corpus\\files")
        assert result == "docs/corpus/files"


class TestValidateRegexPattern:
    """Tests for validate_regex_pattern function."""

    def test_valid_simple_pattern(self):
        """Valid simple regex should compile successfully."""
        is_valid, error, compiled = validate_regex_pattern(r"^test.*$")
        assert is_valid is True
        assert error is None
        assert compiled is not None

    def test_empty_pattern_fails(self):
        """Empty pattern should fail."""
        is_valid, error, compiled = validate_regex_pattern("")
        assert is_valid is False
        assert "cannot be empty" in error
        assert compiled is None

    def test_pattern_too_long_fails(self):
        """Pattern exceeding max length should fail."""
        is_valid, error, compiled = validate_regex_pattern("a" * 1001)
        assert is_valid is False
        assert "maximum length" in error

    def test_invalid_syntax_fails(self):
        """Invalid regex syntax should fail."""
        is_valid, error, compiled = validate_regex_pattern("[unclosed")
        assert is_valid is False
        assert "Invalid regex syntax" in error
        assert compiled is None

    def test_nested_quantifier_rejected(self):
        """Potentially dangerous nested quantifiers should be rejected."""
        # (a+)+ can cause catastrophic backtracking
        is_valid, error, compiled = validate_regex_pattern(r"(a+)+")
        assert is_valid is False
        assert "performance issues" in error

    def test_nested_star_quantifier_rejected(self):
        """Nested * quantifiers should be rejected."""
        is_valid, error, compiled = validate_regex_pattern(r"(a*)*")
        assert is_valid is False
        assert "performance issues" in error

    def test_valid_complex_pattern(self):
        """Valid complex regex without dangerous patterns should pass."""
        pattern = r'^[a-zA-Z][a-zA-Z0-9_]*\.(txt|md|py)$'
        is_valid, error, compiled = validate_regex_pattern(pattern)
        assert is_valid is True
        assert error is None
        assert compiled is not None


class TestEdgeCasesAndSecurityBoundaries:
    """Edge cases and security boundary tests."""

    @pytest.fixture
    def temp_base_dir(self):
        """Create a temporary directory for testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            (base / "allowed").mkdir()
            yield base

    def test_unicode_path_traversal(self, temp_base_dir):
        """Unicode variations of .. should be handled safely."""
        # Various Unicode representations
        unicode_dots = [
            "\u002e\u002e",  # Standard period
            "\uff0e\uff0e",  # Fullwidth period (should not match ..)
        ]
        for dots in unicode_dots:
            try:
                validate_safe_path(f"{dots}/secret", temp_base_dir)
            except ValueError:
                pass  # Expected for traversal attempts

    def test_very_long_path_handling(self, temp_base_dir):
        """Very long paths should be handled without crashing."""
        long_path = "a" * 5000
        try:
            validate_safe_path(long_path, temp_base_dir)
        except (ValueError, OSError):
            pass  # Expected to fail but not crash

    def test_symlink_escape_blocked(self, temp_base_dir):
        """Symlink escape attempts should be blocked by resolve()."""
        # Create symlink pointing outside base
        allowed = temp_base_dir / "allowed"
        symlink = allowed / "escape_link"
        try:
            symlink.symlink_to("/etc")
            with pytest.raises(ValueError, match="access denied"):
                validate_safe_path("allowed/escape_link/passwd", temp_base_dir)
        except OSError:
            pytest.skip("Symlink creation not supported")
        finally:
            if symlink.exists():
                symlink.unlink()

    def test_display_name_control_characters_removed(self):
        """Control characters should be removed from display names."""
        control_chars = "Name\x00\x01\x02\x03"
        result = validate_display_name(control_chars)
        assert "\x00" not in result
        assert "\x01" not in result

    def test_identifier_with_null_byte_fails(self):
        """Identifier with null byte should fail."""
        with pytest.raises(ValueError):
            validate_identifier("valid\x00id")
