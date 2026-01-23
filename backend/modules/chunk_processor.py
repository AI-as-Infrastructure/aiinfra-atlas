"""
Chunk processor module for maintaining parent-source associations.
"""

from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
import hashlib
from datetime import datetime


class ChunkProcessor:
    """Processes documents into chunks while maintaining parent associations."""

    def __init__(self, chunk_size: int = 500, chunk_overlap: int = 50):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def process_document(
        self,
        file_path: Path,
        content: str,
        config: Dict[str, Any],
        parent_metadata: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Process a document into chunks with parent association.

        Args:
            file_path: Path to the source document
            content: Document content
            config: Processing configuration
            parent_metadata: Optional parent document metadata

        Returns:
            List of chunks with parent associations
        """
        # Generate parent document ID
        parent_id = self._generate_document_id(file_path)

        # Extract parent metadata if not provided
        if parent_metadata is None:
            parent_metadata = self._extract_parent_metadata(file_path, content)

        # Create chunks
        chunks = self._create_chunks(content)

        # Process each chunk
        processed_chunks = []
        for i, chunk_text in enumerate(chunks):
            chunk = {
                "id": f"{parent_id}_chunk_{i:04d}",
                "parent_id": parent_id,
                "parent_path": str(file_path),
                "chunk_index": i,
                "total_chunks": len(chunks),
                "text": chunk_text,
                "metadata": {
                    **parent_metadata,  # Inherit all parent metadata
                    "chunk_position": self._get_chunk_position(i, len(chunks)),
                    "chunk_size": len(chunk_text),
                    "processed_at": datetime.now().isoformat()
                }
            }

            # Add filter associations
            chunk["filters"] = self._get_filter_associations(file_path, config)

            processed_chunks.append(chunk)

        return processed_chunks

    def process_batch(
        self,
        documents: List[Tuple[Path, str]],
        config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Process multiple documents in batch.

        Args:
            documents: List of (file_path, content) tuples
            config: Processing configuration

        Returns:
            Processing results with all chunks and statistics
        """
        results = {
            "chunks": [],
            "documents_processed": 0,
            "total_chunks": 0,
            "parent_documents": {},
            "statistics": {}
        }

        for file_path, content in documents:
            # Process document
            chunks = self.process_document(file_path, content, config)

            # Store parent document info
            if chunks:
                parent_id = chunks[0]["parent_id"]
                results["parent_documents"][parent_id] = {
                    "path": str(file_path),
                    "num_chunks": len(chunks),
                    "metadata": chunks[0]["metadata"]
                }

            results["chunks"].extend(chunks)
            results["documents_processed"] += 1
            results["total_chunks"] += len(chunks)

        # Calculate statistics
        results["statistics"] = self._calculate_statistics(results)

        return results

    def process_literary_work(
        self,
        file_path: Path,
        content: str,
        config: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Special processing for literary works (novels, long texts).

        Detects chapters/sections and maintains their structure.
        """
        # Detect chapters or sections
        chapters = self._detect_chapters(content)

        if chapters:
            return self._process_with_chapters(file_path, content, chapters, config)
        else:
            # Process as single document
            return self.process_document(file_path, content, config)

    def _create_chunks(self, content: str) -> List[str]:
        """Create overlapping chunks from content."""
        chunks = []

        # Simple word-based chunking
        words = content.split()

        if len(words) <= self.chunk_size:
            # Document fits in single chunk
            return [content]

        # Create overlapping chunks
        for i in range(0, len(words), self.chunk_size - self.chunk_overlap):
            chunk_words = words[i:i + self.chunk_size]
            chunk_text = ' '.join(chunk_words)
            chunks.append(chunk_text)

            # Stop if we've reached the end
            if i + self.chunk_size >= len(words):
                break

        return chunks

    def _generate_document_id(self, file_path: Path) -> str:
        """Generate unique ID for parent document."""
        # Use hash of file path for consistent IDs
        path_str = str(file_path)
        hash_obj = hashlib.md5(path_str.encode())
        return f"doc_{hash_obj.hexdigest()[:12]}"

    def _extract_parent_metadata(self, file_path: Path, content: str) -> Dict[str, Any]:
        """Extract metadata for parent document."""
        metadata = {
            "filename": file_path.name,
            "file_type": file_path.suffix.lower(),
            "file_size": len(content),
            "parent_dir": file_path.parent.name
        }

        # Extract title if possible
        if content:
            # Try to extract title from first line or heading
            lines = content.split('\n')
            for line in lines[:10]:  # Check first 10 lines
                line = line.strip()
                if line and not line.startswith('#'):
                    metadata["title"] = line[:100]  # First 100 chars as title
                    break

        # Try to detect author from filename or content
        filename = file_path.stem
        if '_' in filename:
            parts = filename.split('_')
            if parts[0].istitle():
                metadata["author"] = parts[0].replace('_', ' ')

        return metadata

    def _get_chunk_position(self, index: int, total: int) -> str:
        """Determine chunk position in document."""
        if total == 1:
            return "single"
        elif index == 0:
            return "beginning"
        elif index == total - 1:
            return "end"
        else:
            position = index / total
            if position < 0.33:
                return "early"
            elif position > 0.67:
                return "late"
            else:
                return "middle"

    def _get_filter_associations(self, file_path: Path, config: Dict[str, Any]) -> List[str]:
        """Get filter IDs associated with this document."""
        filters = []

        filter_config = config.get("filters", {})
        for filter_def in filter_config.get("filters", []):
            pattern = filter_def.get("pattern", "")

            # Simple pattern matching
            if self._matches_filter(file_path, pattern):
                filters.append(filter_def["id"])

        return filters

    def _matches_filter(self, file_path: Path, pattern: str) -> bool:
        """Check if file matches filter pattern."""
        # Simple implementation - can be enhanced
        path_str = str(file_path)

        if "**" in pattern:
            # Wildcard matching
            pattern_parts = pattern.replace("**", "*").split("/")
            for part in pattern_parts:
                if part != "*" and part not in path_str:
                    return False
            return True

        return pattern in path_str

    def _detect_chapters(self, content: str) -> Optional[List[Dict[str, Any]]]:
        """Detect chapter or section boundaries in text."""
        chapters = []

        # Common chapter patterns
        chapter_patterns = [
            r"^Chapter\s+\d+",
            r"^CHAPTER\s+[IVX]+",
            r"^Part\s+\d+",
            r"^\d+\.\s+\w+",
            r"^={3,}$"  # Section dividers
        ]

        lines = content.split('\n')
        current_pos = 0

        for i, line in enumerate(lines):
            for pattern in chapter_patterns:
                import re
                if re.match(pattern, line.strip()):
                    chapters.append({
                        "line": i,
                        "position": current_pos,
                        "title": line.strip()[:100]
                    })
                    break
            current_pos += len(line) + 1  # +1 for newline

        return chapters if len(chapters) > 1 else None

    def _process_with_chapters(
        self,
        file_path: Path,
        content: str,
        chapters: List[Dict[str, Any]],
        config: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Process document with chapter structure."""
        all_chunks = []
        parent_id = self._generate_document_id(file_path)
        parent_metadata = self._extract_parent_metadata(file_path, content)

        for i, chapter in enumerate(chapters):
            # Extract chapter content
            start_pos = chapter["position"]
            end_pos = chapters[i + 1]["position"] if i + 1 < len(chapters) else len(content)
            chapter_content = content[start_pos:end_pos]

            # Create chunks for this chapter
            chapter_chunks = self._create_chunks(chapter_content)

            # Process each chunk
            for j, chunk_text in enumerate(chapter_chunks):
                chunk = {
                    "id": f"{parent_id}_ch{i:02d}_chunk{j:04d}",
                    "parent_id": parent_id,
                    "parent_path": str(file_path),
                    "chapter_index": i,
                    "chapter_title": chapter["title"],
                    "chunk_index": j,
                    "text": chunk_text,
                    "metadata": {
                        **parent_metadata,
                        "chapter": chapter["title"],
                        "chunk_position": self._get_chunk_position(j, len(chapter_chunks)),
                        "processed_at": datetime.now().isoformat()
                    }
                }

                # Add filter associations
                chunk["filters"] = self._get_filter_associations(file_path, config)

                all_chunks.append(chunk)

        return all_chunks

    def _calculate_statistics(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate processing statistics."""
        stats = {
            "avg_chunks_per_doc": 0,
            "avg_chunk_size": 0,
            "total_text_size": 0,
            "chunk_distribution": {}
        }

        if results["documents_processed"] > 0:
            stats["avg_chunks_per_doc"] = results["total_chunks"] / results["documents_processed"]

        if results["chunks"]:
            chunk_sizes = [len(c["text"]) for c in results["chunks"]]
            stats["avg_chunk_size"] = sum(chunk_sizes) / len(chunk_sizes)
            stats["total_text_size"] = sum(chunk_sizes)

            # Distribution by position
            positions = [c["metadata"].get("chunk_position", "unknown") for c in results["chunks"]]
            for pos in positions:
                stats["chunk_distribution"][pos] = stats["chunk_distribution"].get(pos, 0) + 1

        return stats

    def validate_chunk_associations(self, chunks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Validate that all chunks maintain proper parent associations."""
        validation = {
            "valid": True,
            "issues": [],
            "orphan_chunks": [],
            "parent_coverage": {}
        }

        # Group chunks by parent
        by_parent = {}
        for chunk in chunks:
            parent_id = chunk.get("parent_id")
            if not parent_id:
                validation["orphan_chunks"].append(chunk.get("id", "unknown"))
                validation["valid"] = False
            else:
                if parent_id not in by_parent:
                    by_parent[parent_id] = []
                by_parent[parent_id].append(chunk)

        # Check each parent's chunks
        for parent_id, parent_chunks in by_parent.items():
            # Check for sequential chunk indices
            indices = sorted([c.get("chunk_index", -1) for c in parent_chunks])
            expected = list(range(len(indices)))

            if indices != expected:
                validation["issues"].append(
                    f"Parent {parent_id} has non-sequential chunk indices: {indices}"
                )
                validation["valid"] = False

            validation["parent_coverage"][parent_id] = len(parent_chunks)

        if validation["orphan_chunks"]:
            validation["issues"].append(
                f"Found {len(validation['orphan_chunks'])} chunks without parent associations"
            )

        return validation