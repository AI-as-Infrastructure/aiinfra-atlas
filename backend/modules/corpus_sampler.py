"""
Corpus sampling module for validation phase.
Implements minimal viable sample selection for corpus validation.
"""

import random
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from collections import defaultdict
import xml.etree.ElementTree as ET


class CorpusSampler:
    """Handles sampling of corpus documents for validation."""

    def __init__(self, source_path: str):
        self.source_path = Path(source_path)
        if not self.source_path.exists():
            raise ValueError(f"Source path does not exist: {source_path}")

    def get_minimal_sample(
        self,
        filters: List[Dict[str, Any]],
        corpus_files: Optional[List[Path]] = None
    ) -> Dict[str, Any]:
        """
        Get minimal viable sample according to specification rules.

        Rules:
        - Minimum: 10 documents or 5% of corpus (whichever is smaller)
        - Maximum: 50 documents or 10% of corpus (whichever is smaller)
        - Per-filter minimum: 2 documents from each discovered filter
        """
        if corpus_files is None:
            corpus_files = self._get_all_files()

        total_files = len(corpus_files)

        # Calculate sample size bounds
        min_sample = min(10, max(1, int(total_files * 0.05)))
        max_sample = min(50, max(min_sample, int(total_files * 0.10)))

        # Ensure we have at least 2 docs per filter if possible
        min_per_filter = 2
        required_for_filters = len(filters) * min_per_filter

        # Adjust sample size to accommodate filter requirements
        target_sample_size = max(min_sample, min(max_sample, required_for_filters))

        sample = {
            "total_files": total_files,
            "sample_size": target_sample_size,
            "min_sample": min_sample,
            "max_sample": max_sample,
            "sampling_method": self._determine_sampling_method(filters),
            "files": [],
            "by_filter": defaultdict(list)
        }

        # Perform sampling based on method
        if sample["sampling_method"] == "stratified":
            sample["files"] = self._stratified_sample(
                corpus_files, filters, target_sample_size, min_per_filter
            )
        else:
            sample["files"] = self._random_sample(corpus_files, target_sample_size)

        # Categorize by filter
        for file_path in sample["files"]:
            for filter_def in filters:
                if self._matches_filter(file_path, filter_def):
                    sample["by_filter"][filter_def["id"]].append(str(file_path))

        return sample

    def get_stratified_sample(
        self,
        filters: List[Dict[str, Any]],
        min_per_stratum: int = 2
    ) -> Dict[str, List[Path]]:
        """Get stratified sample ensuring representation from each filter."""
        corpus_files = self._get_all_files()
        files_by_filter = defaultdict(list)

        # Categorize files by filter
        for file_path in corpus_files:
            for filter_def in filters:
                if self._matches_filter(file_path, filter_def):
                    files_by_filter[filter_def["id"]].append(file_path)

        # Sample from each filter
        sampled = defaultdict(list)
        for filter_id, files in files_by_filter.items():
            sample_size = min(min_per_stratum, len(files))
            if sample_size > 0:
                sampled[filter_id] = random.sample(files, sample_size)

        return dict(sampled)

    def get_adaptive_sample(
        self,
        corpus_characteristics: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Adjust sample size based on corpus characteristics.

        - Increase sample for heterogeneous corpora
        - Reduce sample for homogeneous corpora
        - Adjust based on metadata extraction success rate
        """
        corpus_files = self._get_all_files()
        base_sample_size = int(len(corpus_files) * 0.05)

        # Heterogeneity factor
        heterogeneity = corpus_characteristics.get("heterogeneity", 0.5)

        # Adjust sample size
        if heterogeneity > 0.7:
            # Highly heterogeneous - increase sample
            adjusted_size = int(base_sample_size * 1.5)
        elif heterogeneity < 0.3:
            # Highly homogeneous - decrease sample
            adjusted_size = int(base_sample_size * 0.7)
        else:
            adjusted_size = base_sample_size

        # Apply bounds
        adjusted_size = max(10, min(50, adjusted_size))

        return {
            "base_size": base_sample_size,
            "adjusted_size": adjusted_size,
            "heterogeneity": heterogeneity,
            "files": random.sample(corpus_files, min(adjusted_size, len(corpus_files)))
        }

    def sample_for_validation(
        self,
        structure_type: str,
        filters: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Sample corpus for validation based on structure type.

        Special handling for:
        - 2-layer structures: Sample from each combination (e.g., AU/1901, NZ/1901)
        - XML corpora: Include diverse XML structures
        - Literary corpora: Sample from beginning, middle, end of long texts
        """
        sample_strategy = {
            "structure_type": structure_type,
            "samples": []
        }

        if structure_type == "two_layer":
            sample_strategy["samples"] = self._sample_two_layer(filters)
        elif structure_type == "xml":
            sample_strategy["samples"] = self._sample_xml_diversity()
        elif structure_type == "literary":
            sample_strategy["samples"] = self._sample_literary_texts()
        else:
            # Default sampling
            corpus_files = self._get_all_files()
            sample_size = min(20, max(10, int(len(corpus_files) * 0.05)))
            sample_strategy["samples"] = random.sample(
                corpus_files,
                min(sample_size, len(corpus_files))
            )

        return sample_strategy

    def _get_all_files(self) -> List[Path]:
        """Get all valid corpus files."""
        valid_extensions = {'.txt', '.xml', '.tei', '.text'}
        files = []

        for file_path in self.source_path.rglob("*"):
            if file_path.is_file() and file_path.suffix.lower() in valid_extensions:
                # Skip hidden files
                if not any(part.startswith('.') for part in file_path.parts):
                    files.append(file_path)

        return files

    def _determine_sampling_method(self, filters: List[Dict[str, Any]]) -> str:
        """Determine the best sampling method."""
        if len(filters) > 0:
            return "stratified"
        return "random"

    def _stratified_sample(
        self,
        corpus_files: List[Path],
        filters: List[Dict[str, Any]],
        target_size: int,
        min_per_filter: int
    ) -> List[Path]:
        """Perform stratified sampling across filters."""
        sampled = set()
        files_by_filter = defaultdict(list)

        # Categorize files by filter
        for file_path in corpus_files:
            matched_filter = False
            for filter_def in filters:
                if self._matches_filter(file_path, filter_def):
                    files_by_filter[filter_def["id"]].append(file_path)
                    matched_filter = True

            # Track unmatched files
            if not matched_filter:
                files_by_filter["_unmatched"].append(file_path)

        # First pass: ensure minimum per filter
        for filter_id, files in files_by_filter.items():
            if filter_id != "_unmatched" and files:
                sample_size = min(min_per_filter, len(files))
                sampled.update(random.sample(files, sample_size))

        # Second pass: fill to target size
        remaining = target_size - len(sampled)
        if remaining > 0:
            # Get all files not yet sampled
            unsampled = [f for f in corpus_files if f not in sampled]
            if unsampled:
                additional = random.sample(unsampled, min(remaining, len(unsampled)))
                sampled.update(additional)

        return list(sampled)

    def _random_sample(self, corpus_files: List[Path], target_size: int) -> List[Path]:
        """Perform simple random sampling."""
        sample_size = min(target_size, len(corpus_files))
        return random.sample(corpus_files, sample_size)

    def _matches_filter(self, file_path: Path, filter_def: Dict[str, Any]) -> bool:
        """Check if file matches filter pattern."""
        rel_path = file_path.relative_to(self.source_path)
        pattern = filter_def.get("pattern", "")

        if filter_def.get("type") == "directory":
            # Simple directory-based matching
            pattern_parts = pattern.replace("**", "*").split("/")
            path_parts = list(rel_path.parts)

            # Basic pattern matching
            if pattern_parts[0] in path_parts:
                return True

        return False

    def _sample_two_layer(self, filters: List[Dict[str, Any]]) -> List[Path]:
        """Sample from two-layer directory structure."""
        samples = []
        combinations = defaultdict(list)

        # Group filters by parent-child combinations
        for filter_def in filters:
            if filter_def.get("parent_id"):
                combo_key = f"{filter_def['parent_id']}/{filter_def['id']}"
                pattern = filter_def.get("pattern", "")

                # Find files matching this combination
                for file_path in self._get_all_files():
                    if self._matches_filter(file_path, filter_def):
                        combinations[combo_key].append(file_path)

        # Sample from each combination
        for combo, files in combinations.items():
            if files:
                sample_size = min(2, len(files))
                samples.extend(random.sample(files, sample_size))

        return samples

    def _sample_xml_diversity(self) -> List[Path]:
        """Sample diverse XML structures."""
        xml_files = [f for f in self._get_all_files() if f.suffix.lower() in {'.xml', '.tei'}]

        if not xml_files:
            return []

        # Try to get diverse structures by sampling from different directories
        by_directory = defaultdict(list)
        for file_path in xml_files:
            parent = file_path.parent
            by_directory[parent].append(file_path)

        samples = []
        # Take at least one from each directory
        for directory, files in by_directory.items():
            samples.append(random.choice(files))

        # Fill to minimum
        remaining = max(0, 10 - len(samples))
        if remaining > 0 and xml_files:
            unsampled = [f for f in xml_files if f not in samples]
            if unsampled:
                samples.extend(random.sample(unsampled, min(remaining, len(unsampled))))

        return samples

    def _sample_literary_texts(self) -> List[Path]:
        """Sample from literary corpus (beginning, middle, end of long texts)."""
        text_files = [f for f in self._get_all_files() if f.suffix.lower() in {'.txt', '.text'}]

        # Group by parent directory (assuming each work is in its own directory)
        by_work = defaultdict(list)
        for file_path in text_files:
            parent = file_path.parent
            by_work[parent].append(file_path)

        samples = []
        for work_dir, files in by_work.items():
            if len(files) > 3:
                # Sample from beginning, middle, end
                sorted_files = sorted(files)
                samples.append(sorted_files[0])  # Beginning
                samples.append(sorted_files[len(sorted_files) // 2])  # Middle
                samples.append(sorted_files[-1])  # End
            else:
                # Take all if few files
                samples.extend(files)

        return samples[:20]  # Limit to reasonable size

    def estimate_processing_time(
        self,
        sample_results: Dict[str, Any],
        mode: str = "cpu"
    ) -> Dict[str, Any]:
        """
        Estimate processing time based on sample processing metrics.
        """
        sample_size = sample_results.get("sample_size", 10)
        sample_time = sample_results.get("processing_time_seconds", 60)
        total_files = sample_results.get("total_files", 1000)

        # Calculate rate
        if sample_size > 0:
            seconds_per_file = sample_time / sample_size
        else:
            seconds_per_file = 6  # Default estimate

        # Adjust for mode
        if mode == "gpu":
            seconds_per_file *= 0.3  # GPU is roughly 3x faster

        # Estimate total time
        total_seconds = total_files * seconds_per_file

        # Add overhead
        overhead_factor = 1.2  # 20% overhead for setup, cleanup, etc.
        total_seconds *= overhead_factor

        # Calculate confidence based on sample size
        confidence = min(0.95, sample_size / 50)  # Max confidence at 50 samples

        return {
            "estimated_seconds": int(total_seconds),
            "estimated_minutes": int(total_seconds / 60),
            "estimated_hours": round(total_seconds / 3600, 1),
            "confidence": confidence,
            "files_per_minute": int(60 / seconds_per_file) if seconds_per_file > 0 else 10,
            "mode": mode
        }