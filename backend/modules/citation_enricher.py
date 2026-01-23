"""
Citation enrichment module for adding citation metadata to chunks.
"""

import re
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime


class CitationEnricher:
    """Enriches document chunks with citation metadata."""

    def __init__(self, citation_config: Dict[str, Any]):
        self.template = citation_config.get("template", "{author}. {title}. {date}. {source}.")
        self.url_pattern = citation_config.get("url_pattern")
        self.metadata_patterns = citation_config.get("metadata_patterns", {})
        self.source_name = citation_config.get("source_name", "Corpus")
        self.source_url = citation_config.get("source_url")

        # Compile regex patterns
        self.compiled_patterns = {}
        for field, pattern in self.metadata_patterns.items():
            try:
                self.compiled_patterns[field] = re.compile(pattern)
            except re.error:
                print(f"Invalid regex pattern for {field}: {pattern}")

    def enrich_chunk(
        self,
        chunk: Dict[str, Any],
        file_path: Path,
        parent_metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Enrich a chunk with citation metadata.

        Args:
            chunk: The chunk to enrich
            file_path: Path to the source file
            parent_metadata: Optional parent document metadata

        Returns:
            Enriched chunk with citation information
        """
        # Extract metadata from filename
        extracted_metadata = self._extract_metadata_from_filename(file_path)

        # Inherit parent metadata if available
        if parent_metadata:
            extracted_metadata = {**parent_metadata, **extracted_metadata}

        # Add source information
        extracted_metadata["source"] = self.source_name
        if self.source_url:
            extracted_metadata["source_url"] = self.source_url

        # Generate citation text
        citation_text = self._generate_citation(extracted_metadata)

        # Generate URL if pattern provided
        url = self._generate_url(extracted_metadata) if self.url_pattern else None

        # Enrich chunk
        enriched_chunk = {
            **chunk,
            "metadata": {
                **chunk.get("metadata", {}),
                **extracted_metadata,
                "citation": citation_text,
                "url": url,
                "file_path": str(file_path),
                "enriched_at": datetime.now().isoformat()
            }
        }

        return enriched_chunk

    def enrich_batch(
        self,
        chunks: List[Dict[str, Any]],
        file_paths: List[Path]
    ) -> List[Dict[str, Any]]:
        """Enrich multiple chunks in batch."""
        enriched = []

        # Group chunks by file
        chunks_by_file = {}
        for chunk, file_path in zip(chunks, file_paths):
            file_str = str(file_path)
            if file_str not in chunks_by_file:
                chunks_by_file[file_str] = []
            chunks_by_file[file_str].append(chunk)

        # Process each file's chunks
        for file_str, file_chunks in chunks_by_file.items():
            file_path = Path(file_str)

            # Extract parent metadata once per file
            parent_metadata = self._extract_metadata_from_filename(file_path)

            # Enrich each chunk
            for chunk in file_chunks:
                enriched.append(self.enrich_chunk(chunk, file_path, parent_metadata))

        return enriched

    def _extract_metadata_from_filename(self, file_path: Path) -> Dict[str, str]:
        """Extract metadata from filename using configured patterns."""
        metadata = {}
        filename = file_path.stem

        for field, pattern in self.compiled_patterns.items():
            match = pattern.search(filename)
            if match:
                # Use first group if available, otherwise full match
                value = match.group(1) if match.groups() else match.group(0)
                metadata[field] = value

        # Try to extract common patterns if not configured
        if not metadata.get("date") and not metadata.get("year"):
            # Look for year pattern
            year_match = re.search(r'\b(1[789]\d{2}|20[012]\d)\b', filename)
            if year_match:
                metadata["year"] = year_match.group(0)

        # Clean and format extracted values
        metadata = self._clean_metadata(metadata)

        return metadata

    def _clean_metadata(self, metadata: Dict[str, str]) -> Dict[str, str]:
        """Clean and format metadata values."""
        cleaned = {}

        for field, value in metadata.items():
            if isinstance(value, str):
                # Clean underscores and hyphens
                value = value.replace('_', ' ').replace('-', ' ')

                # Title case for names
                if field in ["author", "title"]:
                    value = value.title()

                # Format dates
                if field == "date" and len(value) == 8 and value.isdigit():
                    # Convert YYYYMMDD to YYYY-MM-DD
                    value = f"{value[:4]}-{value[4:6]}-{value[6:8]}"

            cleaned[field] = value

        return cleaned

    def _generate_citation(self, metadata: Dict[str, str]) -> str:
        """Generate citation text from metadata using template."""
        citation = self.template

        # Replace placeholders with metadata values
        for field, value in metadata.items():
            placeholder = f"{{{field}}}"
            if placeholder in citation:
                citation = citation.replace(placeholder, str(value))

        # Remove any remaining placeholders
        citation = re.sub(r'\{[^}]+\}', '', citation)

        # Clean up multiple spaces and punctuation
        citation = re.sub(r'\s+', ' ', citation)
        citation = re.sub(r'\.\s*\.', '.', citation)
        citation = citation.strip()

        return citation

    def _generate_url(self, metadata: Dict[str, str]) -> Optional[str]:
        """Generate URL from metadata using pattern."""
        if not self.url_pattern:
            return None

        url = self.url_pattern

        # Replace placeholders with metadata values
        for field, value in metadata.items():
            placeholder = f"{{{field}}}"
            if placeholder in url:
                # URL encode if needed
                url_value = str(value).replace(' ', '%20')
                url = url.replace(placeholder, url_value)

        # Only return if all placeholders were replaced
        if '{' not in url and '}' not in url:
            return url

        return None

    def validate_citation_config(self, sample_metadata: List[Dict[str, str]]) -> Dict[str, Any]:
        """Validate citation configuration against sample metadata."""
        validation = {
            "valid": True,
            "issues": [],
            "coverage": {}
        }

        # Extract placeholders from template
        template_fields = re.findall(r'\{(\w+)\}', self.template)

        # Check coverage for each field
        for field in template_fields:
            count = sum(1 for m in sample_metadata if field in m)
            coverage = count / len(sample_metadata) if sample_metadata else 0
            validation["coverage"][field] = coverage

            if coverage < 0.5:
                validation["issues"].append(
                    f"Low coverage for citation field '{field}': {coverage:.0%}"
                )

        # Check URL pattern if present
        if self.url_pattern:
            url_fields = re.findall(r'\{(\w+)\}', self.url_pattern)
            for field in url_fields:
                if field not in template_fields:
                    count = sum(1 for m in sample_metadata if field in m)
                    coverage = count / len(sample_metadata) if sample_metadata else 0
                    if coverage < 0.5:
                        validation["issues"].append(
                            f"Low coverage for URL field '{field}': {coverage:.0%}"
                        )

        validation["valid"] = len(validation["issues"]) == 0

        return validation

    def generate_test_citations(
        self,
        sample_files: List[Path],
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """Generate test citations from sample files."""
        test_citations = []

        for file_path in sample_files[:limit]:
            metadata = self._extract_metadata_from_filename(file_path)
            metadata["source"] = self.source_name

            citation = self._generate_citation(metadata)
            url = self._generate_url(metadata) if self.url_pattern else None

            test_citations.append({
                "file": file_path.name,
                "metadata": metadata,
                "citation": citation,
                "url": url
            })

        return test_citations