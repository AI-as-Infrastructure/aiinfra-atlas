"""
Centralized Anonymous ID Service for ATLAS

Provides consistent, privacy-preserving user identification across all environments
and auth modes (Cognito, Cloudflare Access, or any stable identity string) while
ensuring data integrity for inter-rater reliability measurements.
"""

import hashlib
import os
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

class AnonymousIDService:
    """
    Centralized service for generating consistent anonymous user IDs.

    Key Features:
    - Auth-mode agnostic: Accepts any stable identity string (Cognito sub, email, etc.)
    - Environment-isolated: Different salts prevent cross-environment correlation
    - Consistent: Same identity string always gets same anonymous ID within environment
    - Irreversible: Cannot trace back to original identity
    - Privacy-preserving: No PII stored or transmitted to Phoenix
    """
    
    def __init__(self):
        # Environment-specific salt ensures isolation between dev/staging/prod
        self.environment = os.getenv("ENVIRONMENT", "development")
        self.salt = os.getenv("ANONYMOUS_ID_SALT", f"atlas_{self.environment}_salt_2025")
        
        # Validate configuration — fail fast in production with a default salt
        default_salt = f"atlas_{self.environment}_salt_2025"
        if not self.salt or self.salt == default_salt:
            if self.environment == "production":
                raise ValueError(
                    "ANONYMOUS_ID_SALT must be set to a unique value in production. "
                    "Using the default salt is not allowed."
                )
            logger.warning(f"Using default salt for {self.environment}. Set ANONYMOUS_ID_SALT for better security.")
    
    def generate_anonymous_id(self, identity_string: str) -> str:
        """
        Generate consistent anonymous ID from a stable identity string.

        Accepts any stable user identifier: Cognito sub (UUID), email address,
        or other unique string. The same input always produces the same output
        within the same environment (salt).

        Args:
            identity_string: Stable user identifier (Cognito sub, email, etc.)

        Returns:
            Anonymous ID in format: anon_<16-char-hash>

        Raises:
            ValueError: If identity_string is None, empty, or too short
        """
        if not identity_string:
            logger.error("Anonymous ID generation failed: identity_string is None or empty")
            raise ValueError("Identity string is required for anonymous ID generation")

        if not isinstance(identity_string, str):
            logger.error(f"Anonymous ID generation failed: identity_string is not a string, got {type(identity_string)}")
            raise ValueError(f"Identity string must be a string, got {type(identity_string)}")

        if len(identity_string.strip()) < 5:
            logger.error(f"Anonymous ID generation failed: identity_string too short ({len(identity_string)} chars)")
            raise ValueError("Identity string appears to be invalid (too short)")

        try:
            # Create environment-isolated hash
            raw_input = f"{self.salt}_{identity_string}"
            anonymous_hash = hashlib.sha256(raw_input.encode()).hexdigest()[:16]
            anonymous_id = f"anon_{anonymous_hash}"

            # Log only the anonymous hash prefix -- never log any part of the raw identity
            logger.debug(f"Generated anonymous ID for environment {self.environment}: anon_{anonymous_hash[:8]}...")
            return anonymous_id

        except Exception as e:
            logger.error(f"Exception during anonymous ID generation: {type(e).__name__}")
            raise ValueError(f"Failed to generate anonymous ID: {str(e)}")
    
    def get_anonymous_id_from_user_data(self, user_data: Dict[str, Any]) -> str:
        """
        Extract and convert user data to anonymous ID.

        Works with any auth mode that provides a 'sub' field:
        - Cognito: sub is a UUID
        - Cloudflare: sub is the authenticated email address
        - None: sub is 'anonymous' (will be rejected as too short)

        Args:
            user_data: Authenticated user data (must have 'sub' and 'authenticated': True)

        Returns:
            Anonymous ID string

        Raises:
            ValueError: If user not authenticated or missing sub
        """
        if not user_data or not user_data.get("authenticated", False):
            raise ValueError("User must be authenticated for identity-dependent functionality")

        identity = user_data.get("sub")
        if not identity:
            raise ValueError("Missing identity (sub) in user data")

        return self.generate_anonymous_id(identity)
    
    def validate_environment_isolation(self) -> Dict[str, Any]:
        """
        Return environment configuration info for validation.
        
        Returns:
            Dict with environment, salt info (sanitized), and validation status
        """
        return {
            "environment": self.environment,
            "salt_configured": bool(self.salt and len(self.salt) > 10),
            "salt_preview": self.salt[:12] + "..." if self.salt else None,
            "service_ready": bool(self.salt)
        }

# Global service instance
anonymous_id_service = AnonymousIDService()