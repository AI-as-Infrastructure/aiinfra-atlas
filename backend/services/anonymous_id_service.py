"""
Centralized Anonymous ID Service for ATLAS

Provides consistent, privacy-preserving user identification across all environments
while ensuring data integrity for inter-rater reliability measurements.
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
    - Environment-isolated: Different salts prevent cross-environment correlation
    - Consistent: Same authenticated user always gets same anonymous ID within environment
    - Irreversible: Cannot trace back to original Cognito sub
    - Privacy-preserving: No PII stored or transmitted to Phoenix
    """
    
    def __init__(self):
        # Environment-specific salt ensures isolation between dev/staging/prod
        self.environment = os.getenv("ENVIRONMENT", "development")
        self.salt = os.getenv("ANONYMOUS_ID_SALT", f"atlas_{self.environment}_salt_2025")
        
        # Validate configuration
        if not self.salt or self.salt == f"atlas_{self.environment}_salt_2025":
            logger.warning(f"Using default salt for {self.environment}. Set ANONYMOUS_ID_SALT for better security.")
    
    def generate_anonymous_id(self, cognito_sub: str) -> str:
        """
        Generate consistent anonymous ID from Cognito sub.
        
        Args:
            cognito_sub: Cognito user sub (UUID) from authenticated user
            
        Returns:
            Anonymous ID in format: anon_<16-char-hash>
            
        Raises:
            ValueError: If cognito_sub is None or empty
        """
        if not cognito_sub:
            logger.error("Anonymous ID generation failed: cognito_sub is None or empty")
            raise ValueError("Cognito sub is required for anonymous ID generation")
        
        if not isinstance(cognito_sub, str):
            logger.error(f"Anonymous ID generation failed: cognito_sub is not a string, got {type(cognito_sub)}")
            raise ValueError(f"Cognito sub must be a string, got {type(cognito_sub)}")
        
        if len(cognito_sub.strip()) < 10:
            logger.error(f"Anonymous ID generation failed: cognito_sub too short ({len(cognito_sub)} chars)")
            raise ValueError("Cognito sub appears to be invalid (too short)")
        
        try:
            # Create environment-isolated hash
            raw_input = f"{self.salt}_{cognito_sub}"
            anonymous_hash = hashlib.sha256(raw_input.encode()).hexdigest()[:16]
            anonymous_id = f"anon_{anonymous_hash}"
            
            # Sanitized logging (first 8 chars of hash only)
            logger.debug(f"Generated anonymous ID for environment {self.environment}: anon_{anonymous_hash[:8]}... from Cognito sub {cognito_sub[:8]}...")
            return anonymous_id
            
        except Exception as e:
            logger.error(f"Exception during anonymous ID generation: {e}", exc_info=True)
            raise ValueError(f"Failed to generate anonymous ID: {str(e)}")
    
    def get_anonymous_id_from_user_data(self, user_data: Dict[str, Any]) -> str:
        """
        Extract and convert user data to anonymous ID.
        
        Args:
            user_data: Authenticated user data from Cognito (must have 'sub' and 'authenticated': True)
            
        Returns:
            Anonymous ID string
            
        Raises:
            ValueError: If user not authenticated or missing sub
        """
        if not user_data or not user_data.get("authenticated", False):
            raise ValueError("User must be authenticated for inter-rater functionality")
        
        cognito_sub = user_data.get("sub")
        if not cognito_sub:
            raise ValueError("Missing Cognito sub in user data")
        
        return self.generate_anonymous_id(cognito_sub)
    
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