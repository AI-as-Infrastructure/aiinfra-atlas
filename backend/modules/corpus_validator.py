"""
Corpus validation module for checking consistency and detecting issues.
"""

import re
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from collections import defaultdict, Counter
import xml.etree.ElementTree as ET


class CorpusValidator:
    """Validates corpus structure and metadata extraction."""

    def __init__(self, source_path: str):
        self.source_path = Path(source_path)
        self.issues = []
        self.warnings = []

    def validate_sample(
        self,
        sample_files: List[Path],
        config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Validate sample files and detect issues.
        """
        validation_result = {
            "valid": True,
            "issues": [],
            "warnings": [],
            "metadata_extraction": {},
            "filter_coverage": {},
            "consistency": {},
            "recommendations": []
        }

        # Run validation checks
        validation_result["metadata_extraction"] = self._validate_metadata_extraction(
            sample_files, config.get("citation", {})
        )

        validation_result["consistency"] = self._check_naming_consistency(sample_files)

        validation_result["filter_coverage"] = self._analyze_filter_coverage(
            sample_files, config.get("filters", {})
        )

        # Check for citation template validity
        citation_issues = self._validate_citation_template(
            config.get("citation", {}),
            validation_result["metadata_extraction"]
        )
        validation_result["issues"].extend(citation_issues)

        # XML structure validation if applicable
        if any(f.suffix.lower() in {'.xml', '.tei'} for f in sample_files):
            xml_validation = self._validate_xml_structure(sample_files)
            validation_result["xml_structure"] = xml_validation
            if xml_validation.get("issues"):
                validation_result["issues"].extend(xml_validation["issues"])

        # Determine overall validity
        validation_result["valid"] = len(validation_result["issues"]) == 0

        # Generate recommendations
        validation_result["recommendations"] = self._generate_recommendations(validation_result)

        return validation_result

    def detect_issues(self, sample_files: List[Path]) -> List[Dict[str, Any]]:
        """
        Detect various issues in the corpus sample.
        """
        issues = []

        # Check for empty files
        for file_path in sample_files:
            if file_path.exists() and file_path.stat().st_size == 0:
                issues.append({
                    "type": "empty_file",
                    "severity": "warning",
                    "file": str(file_path),
                    "message": f"Empty file: {file_path.name}"
                })

        # Check for encoding issues
        for file_path in sample_files:
            if file_path.suffix.lower() in {'.txt', '.text'}:
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        f.read(1000)
                except UnicodeDecodeError:
                    issues.append({
                        "type": "encoding_error",
                        "severity": "error",
                        "file": str(file_path),
                        "message": f"Encoding error in: {file_path.name}"
                    })

        # Check for unusually large files
        for file_path in sample_files:
            if file_path.exists():
                size_mb = file_path.stat().st_size / (1024 * 1024)
                if size_mb > 100:
                    issues.append({
                        "type": "large_file",
                        "severity": "warning",
                        "file": str(file_path),
                        "message": f"Large file ({size_mb:.1f} MB): {file_path.name}"
                    })

        return issues

    def _validate_metadata_extraction(
        self,
        sample_files: List[Path],
        citation_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Validate metadata extraction from filenames."""
        patterns = citation_config.get("metadata_patterns", {})
        extraction_results = {
            "success_rate": 0,
            "extracted_fields": defaultdict(list),
            "failed_files": [],
            "coverage": {}
        }

        if not patterns:
            # Use default patterns
            patterns = {
                "date": r"(\d{4}[-_]\d{2}[-_]\d{2}|\d{8})",
                "year": r"(\d{4})",
                "author": r"^([A-Z][a-z]+(?:_[A-Z][a-z]+)*)",
                "title": r"(?:^|_)([A-Z][a-z]+(?:_[A-Z][a-z]+)*)"
            }

        successful = 0
        for file_path in sample_files:
            filename = file_path.stem
            extracted_any = False

            for field, pattern in patterns.items():
                try:
                    match = re.search(pattern, filename)
                    if match:
                        extraction_results["extracted_fields"][field].append({
                            "file": file_path.name,
                            "value": match.group(1) if match.groups() else match.group(0)
                        })
                        extracted_any = True
                except re.error:
                    pass

            if extracted_any:
                successful += 1
            else:
                extraction_results["failed_files"].append(file_path.name)

        # Calculate success rate
        if sample_files:
            extraction_results["success_rate"] = successful / len(sample_files)

        # Calculate field coverage
        for field in patterns:
            count = len(extraction_results["extracted_fields"][field])
            extraction_results["coverage"][field] = count / len(sample_files) if sample_files else 0

        return extraction_results

    def _check_naming_consistency(self, sample_files: List[Path]) -> Dict[str, Any]:
        """Check filename naming consistency."""
        consistency = {
            "consistent": True,
            "patterns_found": [],
            "inconsistencies": []
        }

        if not sample_files:
            return consistency

        # Analyze naming patterns
        patterns = {
            "date_prefix": re.compile(r'^\d{4}'),
            "id_format": re.compile(r'^[A-Z]+-[A-Z]+-\d+'),
            "underscore_separated": re.compile(r'^[\w]+(?:_[\w]+)+$'),
            "hyphen_separated": re.compile(r'^[\w]+(?:-[\w]+)+$'),
            "camel_case": re.compile(r'^[A-Z][a-z]+(?:[A-Z][a-z]+)*$')
        }

        pattern_counts = Counter()

        for file_path in sample_files:
            filename = file_path.stem
            for pattern_name, pattern_re in patterns.items():
                if pattern_re.match(filename):
                    pattern_counts[pattern_name] += 1

        # Determine consistency
        if pattern_counts:
            most_common = pattern_counts.most_common(1)[0]
            consistency["patterns_found"] = list(pattern_counts.keys())

            # If most common pattern doesn't cover at least 70% of files, flag as inconsistent
            coverage = most_common[1] / len(sample_files)
            if coverage < 0.7:
                consistency["consistent"] = False
                consistency["inconsistencies"].append(
                    f"Multiple naming patterns detected. Most common: {most_common[0]} ({coverage:.0%})"
                )

        return consistency

    def _analyze_filter_coverage(
        self,
        sample_files: List[Path],
        filter_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Analyze how well filters cover the sample files."""
        coverage = {
            "total_filters": len(filter_config.get("filters", [])),
            "filters_with_matches": 0,
            "uncovered_files": [],
            "filter_distribution": defaultdict(int)
        }

        filters = filter_config.get("filters", [])
        if not filters:
            return coverage

        covered_files = set()

        for filter_def in filters:
            filter_id = filter_def.get("id", "unknown")
            pattern = filter_def.get("pattern", "")

            matched_any = False
            for file_path in sample_files:
                if self._file_matches_filter(file_path, pattern):
                    covered_files.add(file_path)
                    coverage["filter_distribution"][filter_id] += 1
                    matched_any = True

            if matched_any:
                coverage["filters_with_matches"] += 1

        # Find uncovered files
        coverage["uncovered_files"] = [
            f.name for f in sample_files if f not in covered_files
        ]

        coverage["coverage_rate"] = len(covered_files) / len(sample_files) if sample_files else 0

        return coverage

    def _validate_citation_template(
        self,
        citation_config: Dict[str, Any],
        metadata_extraction: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Validate citation template against extracted metadata."""
        issues = []
        template = citation_config.get("template", "")

        if not template:
            return issues

        # Extract placeholders from template
        placeholders = re.findall(r'\{(\w+)\}', template)

        # Check if we can extract required fields
        extracted_fields = set(metadata_extraction.get("extracted_fields", {}).keys())

        for placeholder in placeholders:
            if placeholder not in extracted_fields and placeholder not in ["source"]:
                # Check coverage for this field
                coverage = metadata_extraction.get("coverage", {}).get(placeholder, 0)
                if coverage < 0.5:
                    issues.append({
                        "type": "citation_field_missing",
                        "severity": "warning",
                        "field": placeholder,
                        "message": f"Citation field '{placeholder}' has low extraction rate ({coverage:.0%})"
                    })

        return issues

    def _validate_xml_structure(self, sample_files: List[Path]) -> Dict[str, Any]:
        """Validate XML structure for XML-based corpora."""
        xml_validation = {
            "valid": True,
            "issues": [],
            "namespaces": set(),
            "root_elements": set()
        }

        xml_files = [f for f in sample_files if f.suffix.lower() in {'.xml', '.tei'}]

        for xml_file in xml_files:
            try:
                tree = ET.parse(xml_file)
                root = tree.getroot()

                # Collect root element names
                xml_validation["root_elements"].add(root.tag)

                # Collect namespaces
                for elem in root.iter():
                    if '}' in elem.tag:
                        namespace = elem.tag.split('}')[0][1:]
                        xml_validation["namespaces"].add(namespace)

            except ET.ParseError as e:
                xml_validation["valid"] = False
                xml_validation["issues"].append({
                    "type": "xml_parse_error",
                    "severity": "error",
                    "file": xml_file.name,
                    "message": f"XML parse error: {str(e)}"
                })
            except Exception as e:
                xml_validation["issues"].append({
                    "type": "xml_error",
                    "severity": "error",
                    "file": xml_file.name,
                    "message": f"Error processing XML: {str(e)}"
                })

        # Check for consistency in root elements
        if len(xml_validation["root_elements"]) > 1:
            xml_validation["issues"].append({
                "type": "xml_inconsistency",
                "severity": "warning",
                "message": f"Multiple root element types found: {xml_validation['root_elements']}"
            })

        # Convert sets to lists for JSON serialization
        xml_validation["namespaces"] = list(xml_validation["namespaces"])
        xml_validation["root_elements"] = list(xml_validation["root_elements"])

        return xml_validation

    def _file_matches_filter(self, file_path: Path, pattern: str) -> bool:
        """Check if file matches filter pattern."""
        # Simple pattern matching - can be enhanced
        rel_path = str(file_path.relative_to(self.source_path.parent))

        # Convert glob pattern to simple matching
        if "**" in pattern:
            # Match any depth
            pattern_parts = pattern.replace("**", "*").split("/")
            for part in pattern_parts:
                if part != "*" and part not in rel_path:
                    return False
            return True
        else:
            # Direct path matching
            return pattern in rel_path

    def _generate_recommendations(self, validation_result: Dict[str, Any]) -> List[str]:
        """Generate recommendations based on validation results."""
        recommendations = []

        # Check metadata extraction
        metadata = validation_result.get("metadata_extraction", {})
        if metadata.get("success_rate", 0) < 0.5:
            recommendations.append(
                "Consider adjusting metadata extraction patterns - current success rate is low"
            )

        # Check naming consistency
        consistency = validation_result.get("consistency", {})
        if not consistency.get("consistent", True):
            recommendations.append(
                "File naming is inconsistent. Consider standardizing filenames before processing"
            )

        # Check filter coverage
        coverage = validation_result.get("filter_coverage", {})
        if coverage.get("coverage_rate", 0) < 0.8:
            recommendations.append(
                f"Filters only cover {coverage.get('coverage_rate', 0):.0%} of files. Consider adding more filters"
            )

        # Check for uncovered files
        if coverage.get("uncovered_files"):
            count = len(coverage["uncovered_files"])
            recommendations.append(
                f"{count} files are not covered by any filter. Review filter configuration"
            )

        # XML-specific recommendations
        xml_validation = validation_result.get("xml_structure", {})
        if xml_validation and not xml_validation.get("valid", True):
            recommendations.append(
                "XML parsing errors detected. Fix XML structure before processing"
            )

        return recommendations

    def categorize_issues(self, issues: List[Dict[str, Any]]) -> Dict[str, List[Dict]]:
        """Categorize issues by severity and type."""
        categorized = {
            "errors": [],
            "warnings": [],
            "info": [],
            "by_type": defaultdict(list)
        }

        for issue in issues:
            severity = issue.get("severity", "info")
            issue_type = issue.get("type", "unknown")

            if severity == "error":
                categorized["errors"].append(issue)
            elif severity == "warning":
                categorized["warnings"].append(issue)
            else:
                categorized["info"].append(issue)

            categorized["by_type"][issue_type].append(issue)

        return categorized