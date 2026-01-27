"""
URL template processor for building source URLs from metadata.

Supports templates like: https://example.com/doc/{document_id}
Builds: https://example.com/doc/3473
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)


class URLBuilder:
    """Build URLs from templates by substituting metadata variables."""

    def __init__(self, template: Optional[str] = None):
        """
        Initialize with URL template.

        Example template:
            https://parlinfo.aph.gov.au/parlInfo/search/display/display.w3p;query=Id:{document_id}

        Args:
            template: URL template with {variable} placeholders
        """
        self.template = template

        if template:
            logger.info(f"URLBuilder initialized with template: {template}")

    def build_url(self, **kwargs) -> Optional[str]:
        """
        Build URL by substituting variables from metadata.

        Example:
            Template: https://example.com/doc/{document_id}
            Args: document_id="3473"
            Returns: https://example.com/doc/3473

        Args:
            **kwargs: Metadata fields to substitute into template

        Returns:
            Built URL string, or None if no template or substitution fails
        """
        if not self.template:
            return None

        try:
            url = self.template.format(**kwargs)
            logger.debug(f"Built URL: {url}")
            return url
        except KeyError as e:
            logger.warning(f"Missing variable {e} for URL template: {self.template}")
            return None
        except Exception as e:
            logger.error(f"Error building URL from template {self.template}: {e}")
            return None
