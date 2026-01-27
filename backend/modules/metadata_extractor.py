"""
Metadata extraction from filenames and document content.

Supports:
- Filename patterns like: {country_code}_{date}_{document_id}.txt
- Inline URLs from first line: <url>https://example.com</url>
"""

import re
import logging
from typing import Dict, Any, Optional, Tuple

logger = logging.getLogger(__name__)


class MetadataExtractor:
    """Extract metadata from filenames and document content."""

    # Regex for extracting <url>...</url> from first line
    INLINE_URL_PATTERN = re.compile(r'^<url>(.*?)</url>', re.MULTILINE)

    def __init__(self, filename_pattern: Optional[str] = None, extract_inline_urls: bool = False):
        """
        Initialize metadata extractor.

        Args:
            filename_pattern: Pattern with {variable_name} placeholders
            extract_inline_urls: Whether to extract URLs from first line of documents
        """
        self.pattern = filename_pattern
        self.regex = self._compile_pattern(filename_pattern) if filename_pattern else None
        self.extract_inline_urls = extract_inline_urls

        if filename_pattern:
            logger.info(f"MetadataExtractor initialized with pattern: {filename_pattern}")
        if extract_inline_urls:
            logger.info("MetadataExtractor will extract inline URLs from document content")

    def extract_from_filename(self, filename: str) -> Dict[str, Any]:
        """
        Extract metadata fields from filename based on pattern.

        Example:
            Pattern: {country_code}_{date}_{document_id}.txt
            Filename: AU_1901-08-02_3473.txt
            Returns: {"country_code": "AU", "date": "1901-08-02", "document_id": "3473"}

        Args:
            filename: Filename to extract metadata from

        Returns:
            Dictionary of extracted metadata fields, empty dict if no pattern or no match
        """
        if not self.regex:
            return {}

        match = self.regex.match(filename)
        if match:
            extracted = match.groupdict()
            logger.debug(f"Extracted metadata from {filename}: {extracted}")
            return extracted

        logger.debug(f"No metadata match for {filename} with pattern {self.pattern}")
        return {}

    def extract_inline_url(self, content: str) -> Tuple[Optional[str], str]:
        """
        Extract URL from first line of content if present.

        Looks for pattern: <url>https://example.com</url>

        Args:
            content: Document content to extract URL from

        Returns:
            Tuple of (extracted_url, cleaned_content)
            - extracted_url: URL string if found, None otherwise
            - cleaned_content: Content with URL line removed if found, original content otherwise
        """
        if not self.extract_inline_urls:
            return None, content

        match = self.INLINE_URL_PATTERN.search(content)
        if match:
            url = match.group(1).strip()
            # Remove the URL line from content
            cleaned_content = self.INLINE_URL_PATTERN.sub('', content, count=1).lstrip()
            logger.debug(f"Extracted inline URL: {url}")
            return url, cleaned_content

        return None, content

    def _compile_pattern(self, pattern: str) -> re.Pattern:
        r"""
        Convert {variable_name} pattern to regex.

        Converts patterns like:
            {country_code}_{date}_{document_id}.txt
        To regex:
            (?P<country_code>[^_/.]+)_(?P<date>[^_/.]+)_(?P<document_id>[^_/.]+)\.txt

        Args:
            pattern: Pattern with {variable} placeholders

        Returns:
            Compiled regex pattern
        """
        # Escape special regex characters except {, }, and *
        pattern_escaped = re.escape(pattern)

        # Replace escaped \{var\} with named groups: (?P<var>[^_/.]+)
        # [^_/.]+  matches anything except underscore, slash, or dot (common separators)
        regex_pattern = re.sub(
            r'\\{(\w+)\\}',
            r'(?P<\1>[^_/.]+)',
            pattern_escaped
        )

        logger.debug(f"Compiled pattern '{pattern}' to regex: {regex_pattern}")
        return re.compile(regex_pattern)
