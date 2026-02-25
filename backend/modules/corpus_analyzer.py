"""
Corpus analysis module for discovering structure and suggesting filters.

Analyzes corpus directories to identify patterns, extract metadata,
and suggest appropriate filters based on both structure and user hints.
"""

import os
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List, Any, Optional, Set, Tuple
from collections import defaultdict, Counter
import logging

logger = logging.getLogger(__name__)


class CorpusAnalyzer:
    """Analyzes corpus structure and content to suggest configuration."""

    def __init__(self):
        """Initialize the corpus analyzer."""
        self.supported_text_extensions = {'.txt', '.text'}
        self.supported_xml_extensions = {'.xml', '.tei'}
        self.supported_extensions = self.supported_text_extensions | self.supported_xml_extensions

    def analyze_corpus(
        self,
        base_path: str,
        file_types: List[str],
        metadata_hints: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Analyze a corpus directory to discover structure and suggest configuration.

        Args:
            base_path: Root directory of the corpus
            file_types: List of file extensions to consider
            metadata_hints: User-provided metadata to guide analysis

        Returns:
            Analysis results including structure, statistics, and suggestions
        """
        base = Path(base_path)
        if not base.exists():
            raise ValueError(f"Path does not exist: {base_path}")

        # Collect all relevant files
        files = self._collect_files(base, file_types)

        if not files:
            return {
                'error': f'No files of types {file_types} found in {base_path}',
                'total_files': 0
            }

        # Analyze directory structure
        structure_analysis = self._analyze_structure(files, base)

        # Sample files for content analysis
        content_analysis = self._analyze_content(
            files[:min(100, len(files))],  # Sample up to 100 files
            file_types
        )

        # Suggest filters based on all information
        suggested_filters = self._suggest_filters(
            structure_analysis,
            content_analysis,
            metadata_hints
        )

        # Calculate statistics
        stats = self._calculate_stats(files, suggested_filters)

        return {
            'base_path': str(base),
            'total_files': len(files),
            'file_types': file_types,
            'directory_structure': structure_analysis,
            'content_analysis': content_analysis,
            'suggested_filters': suggested_filters,
            'statistics': stats,
            'metadata_hints': metadata_hints
        }

    def _collect_files(self, base: Path, file_types: List[str]) -> List[Path]:
        """Collect all files of specified types."""
        files = []
        for file_type in file_types:
            pattern = f"**/*.{file_type}"
            files.extend(base.glob(pattern))
        return sorted(files)

    def _analyze_structure(self, files: List[Path], base: Path) -> Dict[str, Any]:
        """Analyze directory structure to identify organizational patterns."""
        structure = {
            'depth_levels': {},
            'common_directories': defaultdict(int),
            'naming_patterns': [],
            'hierarchy': {}
        }

        for file_path in files:
            # Get relative path from base
            rel_path = file_path.relative_to(base)
            parts = rel_path.parts[:-1]  # Exclude filename

            # Track directory depth
            depth = len(parts)
            structure['depth_levels'][depth] = structure['depth_levels'].get(depth, 0) + 1

            # Track common directory names at each level
            for i, part in enumerate(parts):
                key = f"level_{i}"
                if key not in structure['common_directories']:
                    structure['common_directories'][key] = Counter()
                structure['common_directories'][key][part] += 1

        # Identify patterns in directory names
        structure['naming_patterns'] = self._identify_directory_patterns(
            structure['common_directories']
        )

        # Determine organizational hierarchy
        structure['hierarchy'] = self._determine_hierarchy(structure)

        return structure

    def _identify_directory_patterns(self, common_dirs: Dict[str, Counter]) -> List[Dict[str, Any]]:
        """Identify patterns in directory naming."""
        patterns = []

        for level, counter in common_dirs.items():
            # Check for year patterns (e.g., 1850, 2023)
            year_pattern = re.compile(r'^(1[0-9]{3}|2[0-9]{3})$')
            years = [d for d in counter.keys() if year_pattern.match(d)]
            if years:
                patterns.append({
                    'type': 'temporal',
                    'level': level,
                    'pattern': 'year',
                    'examples': years[:5],
                    'count': len(years)
                })

            # Check for decade patterns (e.g., 1850s, 1860s)
            decade_pattern = re.compile(r'^(1[0-9]{2}0s|2[0-9]{2}0s)$')
            decades = [d for d in counter.keys() if decade_pattern.match(d)]
            if decades:
                patterns.append({
                    'type': 'temporal',
                    'level': level,
                    'pattern': 'decade',
                    'examples': decades[:5],
                    'count': len(decades)
                })

            # Check for country/region codes (2-3 letter uppercase)
            region_pattern = re.compile(r'^[A-Z]{2,3}$')
            regions = [d for d in counter.keys() if region_pattern.match(d)]
            if regions:
                patterns.append({
                    'type': 'geographical',
                    'level': level,
                    'pattern': 'region_code',
                    'examples': regions[:5],
                    'count': len(regions)
                })

            # Check for person names (capitalized words)
            name_pattern = re.compile(r'^[A-Z][a-z]+(_[A-Z][a-z]+)?$')
            names = [d for d in counter.keys() if name_pattern.match(d)]
            if names:
                patterns.append({
                    'type': 'entity',
                    'level': level,
                    'pattern': 'person_name',
                    'examples': names[:5],
                    'count': len(names)
                })

        return patterns

    def _determine_hierarchy(self, structure: Dict[str, Any]) -> Dict[str, Any]:
        """Determine the organizational hierarchy of the corpus."""
        hierarchy = {
            'primary': None,
            'secondary': None,
            'suggested_organization': []
        }

        patterns = structure['naming_patterns']

        # Determine primary organization (usually level 0)
        level_0_patterns = [p for p in patterns if p['level'] == 'level_0']
        if level_0_patterns:
            # Prefer temporal > geographical > entity
            for pattern_type in ['temporal', 'geographical', 'entity']:
                matching = [p for p in level_0_patterns if p['type'] == pattern_type]
                if matching:
                    hierarchy['primary'] = matching[0]
                    break

        # Determine secondary organization (usually level 1)
        level_1_patterns = [p for p in patterns if p['level'] == 'level_1']
        if level_1_patterns:
            for pattern_type in ['entity', 'temporal', 'geographical']:
                matching = [p for p in level_1_patterns if p['type'] == pattern_type]
                if matching and matching[0] != hierarchy['primary']:
                    hierarchy['secondary'] = matching[0]
                    break

        # Suggest organization based on patterns
        if hierarchy['primary']:
            if hierarchy['primary']['type'] == 'temporal':
                hierarchy['suggested_organization'].append('by_time_period')
            elif hierarchy['primary']['type'] == 'geographical':
                hierarchy['suggested_organization'].append('by_region')
            elif hierarchy['primary']['type'] == 'entity':
                hierarchy['suggested_organization'].append('by_person')

        return hierarchy

    def _analyze_content(self, sample_files: List[Path], file_types: List[str]) -> Dict[str, Any]:
        """Analyze content of sample files to extract metadata patterns."""
        analysis = {
            'xml_elements': Counter() if 'xml' in file_types else None,
            'text_patterns': {},
            'metadata_fields': set(),
            'date_formats': [],
            'entities_found': defaultdict(set)
        }

        for file_path in sample_files:
            if file_path.suffix in self.supported_xml_extensions:
                self._analyze_xml_file(file_path, analysis)
            elif file_path.suffix in self.supported_text_extensions:
                self._analyze_text_file(file_path, analysis)

        # Convert sets to lists for JSON serialization
        analysis['metadata_fields'] = list(analysis['metadata_fields'])
        analysis['entities_found'] = {k: list(v) for k, v in analysis['entities_found'].items()}

        return analysis

    def _analyze_xml_file(self, file_path: Path, analysis: Dict[str, Any]) -> None:
        """Analyze an XML file for metadata elements."""
        try:
            tree = ET.parse(file_path)
            root = tree.getroot()

            # Count all element tags
            for elem in root.iter():
                tag = elem.tag.split('}')[-1]  # Remove namespace if present
                analysis['xml_elements'][tag] += 1

                # Check for common metadata elements
                if tag.lower() in ['author', 'date', 'subject', 'title', 'recipient', 'location']:
                    analysis['metadata_fields'].add(tag.lower())
                    if elem.text:
                        analysis['entities_found'][tag.lower()].add(elem.text.strip()[:50])

                # Look for dates
                if elem.text and re.search(r'\d{4}', elem.text):
                    dates = re.findall(r'\d{4}-\d{2}-\d{2}|\d{4}/\d{2}/\d{2}|\d{4}', elem.text)
                    analysis['date_formats'].extend(dates[:5])

        except ET.ParseError as e:
            logger.warning(f"Failed to parse XML file {file_path}: {e}")
        except Exception as e:
            logger.warning(f"Error analyzing XML file {file_path}: {e}")

    def analyze_tei_corpus(
        self,
        base_path: str,
        sample_size: int = 20,
    ) -> Dict[str, Any]:
        """Analyze a directory for TEI-XML content and discover available metadata.

        Uses the TEI parser's schema discovery to identify available teiHeader
        elements, their frequency, and sample values.

        Args:
            base_path: Directory containing TEI-XML files
            sample_size: Number of files to sample for schema discovery

        Returns:
            Dictionary with TEI-specific analysis including:
                - is_tei_corpus: whether TEI files were found
                - tei_file_count: number of TEI-XML files
                - non_tei_xml_count: number of non-TEI XML files
                - schema_discovery: output from discover_tei_schema
        """
        from backend.modules.tei_xml_parser import is_tei_xml, discover_tei_schema

        base = Path(base_path)
        if not base.exists():
            raise ValueError(f"Path does not exist: {base_path}")

        xml_files = sorted(base.rglob("*.xml"))
        tei_count = sum(1 for f in xml_files if is_tei_xml(f))
        non_tei_count = len(xml_files) - tei_count

        result = {
            "is_tei_corpus": tei_count > 0,
            "tei_file_count": tei_count,
            "non_tei_xml_count": non_tei_count,
            "total_xml_files": len(xml_files),
        }

        if tei_count > 0:
            result["schema_discovery"] = discover_tei_schema(base, sample_size)
        else:
            result["schema_discovery"] = None

        return result

    def _analyze_text_file(self, file_path: Path, analysis: Dict[str, Any]) -> None:
        """Analyze a text file for patterns and metadata."""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read(5000)  # Read first 5KB

                # Look for header patterns (e.g., "Date: 1850-01-01")
                header_pattern = re.compile(r'^([A-Z][a-z]+):\s*(.+)$', re.MULTILINE)
                headers = header_pattern.findall(content)
                for key, value in headers[:10]:
                    analysis['metadata_fields'].add(key.lower())
                    analysis['entities_found'][key.lower()].add(value.strip()[:50])

                # Look for dates
                dates = re.findall(r'\d{4}-\d{2}-\d{2}|\d{4}/\d{2}/\d{2}|\d{4}', content)
                analysis['date_formats'].extend(dates[:5])

        except Exception as e:
            logger.warning(f"Error analyzing text file {file_path}: {e}")

    def _suggest_filters(
        self,
        structure_analysis: Dict[str, Any],
        content_analysis: Dict[str, Any],
        metadata_hints: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Suggest filters based on all available information.

        Priority order:
        1. Directory structure (highest) - explicit organization by user
        2. Metadata hints (medium) - user knowledge about content
        3. Content analysis (lowest) - discovered from sampling
        """
        filters = []
        used_ids = set()

        # Always add an "all" filter first
        filters.append({
            'id': 'all',
            'label': 'All Documents',
            'type': 'all',
            'pattern': '**/*',
            'confidence': 1.0
        })
        used_ids.add('all')

        # Add filters based on directory structure (HIGHEST PRIORITY)
        # These are explicit organizational choices by the user
        structure_filters = self._filters_from_structure(structure_analysis, used_ids)
        filters.extend(structure_filters)

        # Add filters based on metadata hints (MEDIUM PRIORITY)
        # Only if we don't have good structure filters
        if metadata_hints and len(structure_filters) < 3:
            filters.extend(self._filters_from_hints(metadata_hints, structure_analysis, used_ids))

        # Add filters based on content analysis (LOWEST PRIORITY)
        # Only if we have very few filters from structure
        if content_analysis.get('xml_elements') and len(filters) < 5:
            filters.extend(self._filters_from_xml(content_analysis, used_ids))

        return filters

    def _filters_from_hints(
        self,
        hints: Dict[str, Any],
        structure: Dict[str, Any],
        used_ids: Set[str]
    ) -> List[Dict[str, Any]]:
        """Generate filters from user-provided metadata hints."""
        filters = []

        # Time period filters
        if hints.get('time_period_from') and hints.get('time_period_to'):
            start = hints['time_period_from']
            end = hints['time_period_to']
            span = end - start

            if span > 50:
                # Create decade filters
                for decade in range(start // 10 * 10, end + 1, 10):
                    if decade <= end:
                        filter_id = f"{decade}s"
                        if filter_id not in used_ids:
                            filters.append({
                                'id': filter_id,
                                'label': f"{decade}s",
                                'type': 'temporal',
                                'pattern': f"**/{decade}*/**/*",
                                'confidence': 0.8,
                                'source': 'metadata_hint'
                            })
                            used_ids.add(filter_id)
            elif span > 10:
                # Create year filters
                for year in range(start, end + 1):
                    filter_id = str(year)
                    if filter_id not in used_ids:
                        filters.append({
                            'id': filter_id,
                            'label': str(year),
                            'type': 'temporal',
                            'pattern': f"**/{year}/**/*",
                            'confidence': 0.8,
                            'source': 'metadata_hint'
                        })
                        used_ids.add(filter_id)

        # People filters
        if hints.get('people'):
            for person in hints['people'][:10]:  # Limit to 10 people
                person_id = person.lower().replace(' ', '_')
                if person_id not in used_ids:
                    # Try to find matching directories
                    pattern = f"**/{person.replace(' ', '*')}/**/*"
                    filters.append({
                        'id': person_id,
                        'label': person,
                        'type': 'entity',
                        'subtype': 'person',
                        'pattern': pattern,
                        'confidence': 0.9,
                        'source': 'metadata_hint'
                    })
                    used_ids.add(person_id)

        # Topic filters
        if hints.get('topics'):
            for topic in hints['topics'][:10]:
                topic_id = topic.lower().replace(' ', '_')
                if topic_id not in used_ids:
                    filters.append({
                        'id': topic_id,
                        'label': topic.title(),
                        'type': 'thematic',
                        'pattern': f"**/*{topic}*/**/*",
                        'confidence': 0.7,
                        'source': 'metadata_hint'
                    })
                    used_ids.add(topic_id)

        return filters

    def _filters_from_structure(
        self,
        structure: Dict[str, Any],
        used_ids: Set[str]
    ) -> List[Dict[str, Any]]:
        """Generate filters from directory structure patterns.

        Uses folder names directly as filter labels - users should name
        folders meaningfully (e.g., 'Australia' not 'AU').
        """
        filters = []

        # First, create filters for ALL top-level directories (level_0)
        level_0_dirs = structure.get('common_directories', {}).get('level_0', {})
        if level_0_dirs:
            for dir_name, count in level_0_dirs.items():
                filter_id = dir_name.lower().replace(' ', '_')
                if filter_id in used_ids:
                    continue

                # Use the folder name directly as the label
                # Users should name folders meaningfully
                filters.append({
                    'id': filter_id,
                    'label': dir_name,  # Use exact folder name
                    'type': 'structural',  # Based on structure, not content
                    'pattern': f"{dir_name}/**/*",
                    'confidence': 0.95,  # High confidence for explicit folder structure
                    'source': 'directory_structure',
                    'level': 'level_0',
                    'document_count': count
                })
                used_ids.add(filter_id)

        # Then add filters for patterns found in deeper levels
        for pattern in structure.get('naming_patterns', []):
            if pattern['level'] == 'level_0':
                continue  # Already handled above

            if pattern['count'] < 2:
                continue  # Skip if only one instance

            # Create filters for pattern-based discoveries at deeper levels
            for example in pattern['examples'][:3]:  # Limit to top 3
                filter_id = f"{pattern['level']}_{example.lower()}"
                if filter_id in used_ids:
                    continue

                filters.append({
                    'id': filter_id,
                    'label': f"{example} ({pattern['level'].replace('_', ' ')})",
                    'type': pattern['type'],
                    'pattern': f"**/{example}/**/*",
                    'confidence': 0.75,  # Lower confidence for deeper patterns
                    'source': 'structure_pattern',
                    'level': pattern['level']
                })
                used_ids.add(filter_id)

        return filters

    def _filters_from_xml(
        self,
        content: Dict[str, Any],
        used_ids: Set[str]
    ) -> List[Dict[str, Any]]:
        """Generate filters from XML content analysis."""
        filters = []

        # Only create filters for elements that appear frequently
        common_elements = {
            tag: count for tag, count in content['xml_elements'].items()
            if count > len(content['xml_elements']) * 0.5  # Appears in >50% of samples
        }

        for field, values in content.get('entities_found', {}).items():
            if len(values) > 1 and field in ['author', 'recipient', 'subject']:
                for value in list(values)[:5]:
                    filter_id = f"{field}_{value[:20].lower().replace(' ', '_')}"
                    if filter_id not in used_ids:
                        filters.append({
                            'id': filter_id,
                            'label': f"{field.title()}: {value}",
                            'type': 'metadata',
                            'xpath': f"//{field}[contains(., '{value}')]",
                            'confidence': 0.75,
                            'source': 'content'
                        })
                        used_ids.add(filter_id)

        return filters

    def _expand_region_code(self, code: str) -> str:
        """Return the folder name as-is for use as a filter label."""
        # Don't expand - let users name their folders meaningfully
        # e.g., "Australia" instead of "AU" if they want that label
        return code

    def _calculate_stats(
        self,
        files: List[Path],
        filters: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Calculate statistics for the corpus."""
        stats = {
            'total_files': len(files),
            'total_size_mb': sum(f.stat().st_size for f in files) / 1024 / 1024,
            'file_types': Counter(f.suffix for f in files),
            'avg_file_size_kb': sum(f.stat().st_size for f in files) / len(files) / 1024 if files else 0,
            'filter_coverage': {}
        }

        # Estimate filter coverage (simplified - actual implementation would test patterns)
        for filter_def in filters:
            if filter_def['id'] != 'all':
                # This is a rough estimate - actual implementation would test the pattern
                stats['filter_coverage'][filter_def['id']] = {
                    'estimated_docs': len(files) // max(len(filters) - 1, 1),
                    'confidence': filter_def.get('confidence', 0.5)
                }

        return stats