#!/usr/bin/env python3
"""
Universal corpus store builder.

Config-driven corpus store creation that replaces hardcoded Hansard-specific logic
with a flexible system that can handle any corpus structure.
"""

import os
import sys
import json
import time
import asyncio
import logging
import hashlib
from pathlib import Path
from typing import Dict, List, Any, Optional, Callable, AsyncIterator
from datetime import datetime
import psutil
import torch

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from backend.modules.corpus_config import CorpusConfig, CorpusFilter
from backend.modules.github_corpus import GitHubCorpusManager

# LangChain imports
from langchain.text_splitter import RecursiveCharacterTextSplitter, CharacterTextSplitter
from langchain_community.document_loaders import DirectoryLoader, TextLoader, UnstructuredXMLLoader
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain.schema import Document

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class BuildProgressTracker:
    """Tracks and reports build progress."""

    def __init__(self, total_docs: int = 0, callback: Optional[Callable] = None):
        """Initialize progress tracker."""
        self.total_docs = total_docs
        self.processed_docs = 0
        self.current_doc = ""
        self.current_chunk = 0
        self.start_time = time.time()
        self.callback = callback
        self.errors = []
        self.warnings = []
        self.filter_progress = {}
        self.paused = False
        self.checkpoint_file = Path("create/output/.build_checkpoint.json")

    async def update(self, doc_path: str, chunk_num: int = 0, filter_id: str = None):
        """Update progress and notify callback."""
        self.current_doc = doc_path
        self.current_chunk = chunk_num

        if filter_id:
            if filter_id not in self.filter_progress:
                self.filter_progress[filter_id] = {"processed": 0, "total": 0}
            self.filter_progress[filter_id]["processed"] += 1

        progress_data = self.get_progress()

        if self.callback:
            await self.callback(progress_data)

        # Save checkpoint periodically (every 10 docs)
        if self.processed_docs % 10 == 0:
            self.save_checkpoint()

    def get_progress(self) -> Dict[str, Any]:
        """Get current progress data."""
        elapsed = time.time() - self.start_time
        docs_per_second = self.processed_docs / elapsed if elapsed > 0 else 0

        if docs_per_second > 0:
            remaining_docs = self.total_docs - self.processed_docs
            estimated_remaining = remaining_docs / docs_per_second
        else:
            estimated_remaining = 0

        return {
            "status": "paused" if self.paused else "building",
            "percentage": (self.processed_docs / self.total_docs * 100) if self.total_docs > 0 else 0,
            "processed_documents": self.processed_docs,
            "total_documents": self.total_docs,
            "current_document": self.current_doc,
            "current_chunk": self.current_chunk,
            "elapsed_seconds": elapsed,
            "estimated_remaining_seconds": estimated_remaining,
            "docs_per_second": docs_per_second,
            "errors": len(self.errors),
            "warnings": len(self.warnings),
            "filter_progress": self.filter_progress,
            "memory": self._get_memory_stats(),
            "performance": self._get_performance_stats()
        }

    def _get_memory_stats(self) -> Dict[str, float]:
        """Get current memory usage statistics."""
        memory = psutil.virtual_memory()
        gpu_memory = {}

        if torch.cuda.is_available():
            gpu_memory = {
                "gpu_allocated_gb": torch.cuda.memory_allocated() / 1e9,
                "gpu_reserved_gb": torch.cuda.memory_reserved() / 1e9,
                "gpu_percent": (torch.cuda.memory_allocated() / torch.cuda.get_device_properties(0).total_memory) * 100
            }

        return {
            "ram_used_gb": memory.used / 1e9,
            "ram_percent": memory.percent,
            "ram_available_gb": memory.available / 1e9,
            **gpu_memory
        }

    def _get_performance_stats(self) -> Dict[str, float]:
        """Get performance statistics."""
        return {
            "cpu_percent": psutil.cpu_percent(interval=0.1),
            "disk_io_read_mb": psutil.disk_io_counters().read_bytes / 1e6 if hasattr(psutil.disk_io_counters(), 'read_bytes') else 0,
            "disk_io_write_mb": psutil.disk_io_counters().write_bytes / 1e6 if hasattr(psutil.disk_io_counters(), 'write_bytes') else 0
        }

    def save_checkpoint(self):
        """Save progress checkpoint for recovery."""
        checkpoint = {
            "processed_docs": self.processed_docs,
            "total_docs": self.total_docs,
            "filter_progress": self.filter_progress,
            "timestamp": datetime.now().isoformat()
        }

        self.checkpoint_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.checkpoint_file, 'w') as f:
            json.dump(checkpoint, f)

    def load_checkpoint(self) -> bool:
        """Load checkpoint if available."""
        if self.checkpoint_file.exists():
            try:
                with open(self.checkpoint_file, 'r') as f:
                    checkpoint = json.load(f)
                self.processed_docs = checkpoint["processed_docs"]
                self.filter_progress = checkpoint["filter_progress"]
                logger.info(f"Loaded checkpoint: {self.processed_docs}/{self.total_docs} documents processed")
                return True
            except Exception as e:
                logger.warning(f"Failed to load checkpoint: {e}")
        return False

    def pause(self):
        """Pause progress tracking."""
        self.paused = True
        self.save_checkpoint()

    def resume(self):
        """Resume progress tracking."""
        self.paused = False


class SystemRequirementsChecker:
    """Check system capabilities for corpus building."""

    @staticmethod
    def check_requirements(doc_count: int) -> Dict[str, Any]:
        """Check if system meets requirements for building corpus."""
        requirements = {
            "cpu": {
                "cores": psutil.cpu_count(logical=False),
                "threads": psutil.cpu_count(logical=True),
                "available": True
            },
            "gpu": {
                "available": torch.cuda.is_available(),
                "count": torch.cuda.device_count() if torch.cuda.is_available() else 0,
                "name": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
                "memory_gb": torch.cuda.get_device_properties(0).total_memory / 1e9 if torch.cuda.is_available() else 0
            },
            "memory": {
                "total_gb": psutil.virtual_memory().total / 1e9,
                "available_gb": psutil.virtual_memory().available / 1e9,
                "required_gb": max(4.0, doc_count * 0.001),  # Rough estimate
                "sufficient": psutil.virtual_memory().available / 1e9 > max(4.0, doc_count * 0.001)
            },
            "disk": {
                "free_gb": psutil.disk_usage('/').free / 1e9,
                "required_gb": doc_count * 0.005,  # Rough estimate
                "sufficient": psutil.disk_usage('/').free / 1e9 > doc_count * 0.005
            }
        }

        # Check for critical issues
        issues = []
        if not requirements["memory"]["sufficient"]:
            issues.append(f"Insufficient memory: {requirements['memory']['available_gb']:.1f}GB available, "
                         f"{requirements['memory']['required_gb']:.1f}GB required")

        if not requirements["disk"]["sufficient"]:
            issues.append(f"Insufficient disk space: {requirements['disk']['free_gb']:.1f}GB available, "
                         f"{requirements['disk']['required_gb']:.1f}GB required")

        requirements["issues"] = issues
        requirements["can_proceed"] = len(issues) == 0

        return requirements


class UniversalCorpusBuilder:
    """Universal corpus builder that uses configuration to build any corpus."""

    def __init__(self, config: CorpusConfig, mode: str = "cpu"):
        """
        Initialize corpus builder.

        Args:
            config: Corpus configuration
            mode: Processing mode ('cpu' or 'gpu')
        """
        self.config = config
        self.mode = mode
        self.progress_tracker = None
        self.documents = []
        self.vector_store = None
        self.embeddings = None
        self.output_dir = Path("create/output")
        self.output_dir.mkdir(parents=True, exist_ok=True)

    async def build(self, progress_callback: Optional[Callable] = None) -> Dict[str, Any]:
        """
        Build corpus with progress tracking.

        Args:
            progress_callback: Async callback for progress updates

        Returns:
            Build results including paths to generated files
        """
        logger.info(f"Starting corpus build: {self.config.metadata.name}")
        logger.info(f"Processing mode: {self.mode}")

        # Initialize progress tracker
        self.progress_tracker = BuildProgressTracker(callback=progress_callback)

        try:
            # Step 1: Fetch source if from GitHub
            source_path = await self._fetch_source()

            # Step 2: Load documents
            await self._load_documents(source_path)

            # Step 3: Initialize embeddings
            self._initialize_embeddings()

            # Step 4: Create vector store
            await self._create_vector_store()

            # Step 5: Generate manifest
            manifest_path = self._generate_manifest()

            # Step 6: Generate BM25 corpus
            bm25_path = await self._generate_bm25_corpus()

            # Step 7: Save configuration
            config_path = self._save_config()

            # Mark as complete
            if progress_callback:
                await progress_callback({
                    "status": "completed",
                    "percentage": 100,
                    "message": "Corpus build completed successfully"
                })

            return {
                "success": True,
                "vector_store_path": str(self.output_dir / "chroma_db"),
                "manifest_path": str(manifest_path),
                "bm25_corpus_path": str(bm25_path),
                "config_path": str(config_path),
                "documents_processed": len(self.documents),
                "errors": self.progress_tracker.errors,
                "warnings": self.progress_tracker.warnings
            }

        except Exception as e:
            logger.error(f"Build failed: {e}")
            if progress_callback:
                await progress_callback({
                    "status": "failed",
                    "error": str(e)
                })
            raise

    async def _fetch_source(self) -> Path:
        """Fetch source files from local or GitHub."""
        if self.config.source.type == "github":
            logger.info(f"Fetching corpus from GitHub: {self.config.source.location}")
            github_manager = GitHubCorpusManager()
            return github_manager.fetch_corpus(
                repo_url=self.config.source.location,
                branch=self.config.source.branch or "main",
                path=self.config.source.path or ""
            )
        else:
            source_path = Path(self.config.source.location)
            if not source_path.exists():
                raise ValueError(f"Source path does not exist: {source_path}")
            return source_path

    async def _load_documents(self, source_path: Path):
        """Load documents from source directory."""
        logger.info(f"Loading documents from {source_path}")

        all_docs = []

        for file_type in self.config.source.file_types:
            logger.info(f"Loading {file_type} files...")

            if file_type == "txt":
                loader = DirectoryLoader(
                    str(source_path),
                    glob=f"**/*.{file_type}",
                    loader_cls=TextLoader,
                    loader_kwargs={"encoding": "utf-8", "autodetect_encoding": True}
                )
            elif file_type == "xml":
                loader = DirectoryLoader(
                    str(source_path),
                    glob=f"**/*.{file_type}",
                    loader_cls=UnstructuredXMLLoader
                )
            else:
                logger.warning(f"Unsupported file type: {file_type}")
                continue

            try:
                docs = loader.load()
                all_docs.extend(docs)
                logger.info(f"Loaded {len(docs)} {file_type} files")
            except Exception as e:
                logger.error(f"Error loading {file_type} files: {e}")
                self.progress_tracker.errors.append(str(e))

        # Apply filters to documents
        self.documents = self._apply_filters(all_docs)
        self.progress_tracker.total_docs = len(self.documents)

        logger.info(f"Total documents after filtering: {len(self.documents)}")

    def _apply_filters(self, documents: List[Document]) -> List[Document]:
        """Apply configured filters to documents."""
        if not self.config.filters:
            return documents

        filtered_docs = []

        for doc in documents:
            # Determine which filter this document belongs to
            doc_filter = self._match_document_to_filter(doc)
            if doc_filter:
                # Add filter metadata
                doc.metadata["corpus"] = doc_filter.id
                doc.metadata["corpus_label"] = doc_filter.label
                filtered_docs.append(doc)

                # Update filter progress
                if doc_filter.id not in self.progress_tracker.filter_progress:
                    self.progress_tracker.filter_progress[doc_filter.id] = {"processed": 0, "total": 0}
                self.progress_tracker.filter_progress[doc_filter.id]["total"] += 1

        return filtered_docs

    def _match_document_to_filter(self, doc: Document) -> Optional[CorpusFilter]:
        """Match a document to a configured filter."""
        doc_path = doc.metadata.get("source", "")

        for filter_config in self.config.filters:
            # Check if document matches filter pattern
            if filter_config.pattern:
                # Simple pattern matching (could be enhanced with glob)
                pattern_parts = filter_config.pattern.replace("**", "").replace("*", "").strip("/").split("/")
                if all(part in doc_path for part in pattern_parts if part):
                    return filter_config

            # Check metadata field matching
            if filter_config.metadata_field and filter_config.metadata_field in doc.metadata:
                return filter_config

        # Default to first filter or None
        return self.config.filters[0] if self.config.filters else None

    def _initialize_embeddings(self):
        """Initialize embedding model."""
        logger.info(f"Initializing embeddings: {self.config.embeddings.model}")

        device = "cuda" if self.mode == "gpu" and torch.cuda.is_available() else "cpu"

        model_kwargs = {"device": device}
        if device == "cuda":
            model_kwargs["trust_remote_code"] = True

        encode_kwargs = {
            "normalize_embeddings": True,
            "batch_size": self.config.embeddings.batch_size
        }

        self.embeddings = HuggingFaceEmbeddings(
            model_name=self.config.embeddings.model,
            model_kwargs=model_kwargs,
            encode_kwargs=encode_kwargs
        )

        logger.info(f"Embeddings initialized on {device}")

    async def _create_vector_store(self):
        """Create vector store with documents."""
        logger.info("Creating vector store...")

        # Split documents into chunks
        splitter = self._get_text_splitter()
        all_chunks = []

        for i, doc in enumerate(self.documents):
            # Update progress
            await self.progress_tracker.update(
                doc_path=doc.metadata.get("source", f"doc_{i}"),
                filter_id=doc.metadata.get("corpus")
            )

            # Check if paused
            while self.progress_tracker.paused:
                await asyncio.sleep(1)

            # Split document
            try:
                chunks = splitter.split_documents([doc])
                all_chunks.extend(chunks)
            except Exception as e:
                logger.warning(f"Error splitting document: {e}")
                self.progress_tracker.warnings.append(str(e))

            self.progress_tracker.processed_docs += 1

        logger.info(f"Created {len(all_chunks)} chunks from {len(self.documents)} documents")

        # Create vector store
        persist_dir = self.output_dir / "chroma_db"
        persist_dir.mkdir(parents=True, exist_ok=True)

        self.vector_store = Chroma.from_documents(
            documents=all_chunks,
            embedding=self.embeddings,
            collection_name=self.config.vector_store.collection_name,
            persist_directory=str(persist_dir)
        )

        # Persist the vector store
        self.vector_store.persist()
        logger.info(f"Vector store created and persisted to {persist_dir}")

    def _get_text_splitter(self):
        """Get appropriate text splitter based on configuration."""
        if self.config.embeddings.chunk_size:
            return RecursiveCharacterTextSplitter(
                chunk_size=self.config.embeddings.chunk_size,
                chunk_overlap=self.config.embeddings.chunk_overlap,
                length_function=len
            )
        else:
            return CharacterTextSplitter(
                chunk_size=1000,
                chunk_overlap=100,
                length_function=len
            )

    def _generate_manifest(self) -> Path:
        """Generate manifest.json with corpus metadata."""
        logger.info("Generating manifest...")

        # Calculate statistics
        stats = {
            "total_documents": len(self.documents),
            "total_chunks": self.vector_store._collection.count() if self.vector_store else 0,
            "filters": {}
        }

        for filter_id, progress in self.progress_tracker.filter_progress.items():
            stats["filters"][filter_id] = progress

        # Create manifest
        manifest = {
            "version": "1.1",
            "created": datetime.now().isoformat(),
            "metadata": self.config.metadata.dict(),
            "source": self.config.source.dict(),
            "embeddings": self.config.embeddings.dict(),
            "vector_store": self.config.vector_store.dict(),
            "statistics": stats,
            "fields": {
                "corpus": {
                    "type": "enum",
                    "values": [f.id for f in self.config.filters]
                }
            }
        }

        manifest_path = self.output_dir / "manifest.json"
        with open(manifest_path, 'w') as f:
            json.dump(manifest, f, indent=2)

        logger.info(f"Manifest saved to {manifest_path}")
        return manifest_path

    async def _generate_bm25_corpus(self) -> Path:
        """Generate BM25 corpus for hybrid search."""
        logger.info("Generating BM25 corpus...")

        bm25_path = self.output_dir / "bm25_corpus.jsonl"

        with open(bm25_path, 'w') as f:
            for doc in self.documents:
                bm25_doc = {
                    "id": hashlib.md5(doc.page_content.encode()).hexdigest(),
                    "content": doc.page_content,
                    "metadata": doc.metadata
                }
                f.write(json.dumps(bm25_doc) + "\n")

        logger.info(f"BM25 corpus saved to {bm25_path}")
        return bm25_path

    def _save_config(self) -> Path:
        """Save configuration to output directory."""
        config_path = self.output_dir / "corpus_config.yaml"
        self.config.to_yaml(str(config_path))
        logger.info(f"Configuration saved to {config_path}")
        return config_path


async def build_corpus_from_config(
    config_path: str,
    mode: str = "cpu",
    progress_callback: Optional[Callable] = None
) -> Dict[str, Any]:
    """
    Build corpus from configuration file.

    Args:
        config_path: Path to corpus configuration YAML
        mode: Processing mode ('cpu' or 'gpu')
        progress_callback: Optional async callback for progress updates

    Returns:
        Build results
    """
    # Load configuration
    config = CorpusConfig.from_yaml(config_path)

    # Check system requirements
    checker = SystemRequirementsChecker()
    requirements = checker.check_requirements(1000)  # Estimate

    if not requirements["can_proceed"]:
        raise RuntimeError(f"System requirements not met: {requirements['issues']}")

    # Build corpus
    builder = UniversalCorpusBuilder(config, mode)
    return await builder.build(progress_callback)


if __name__ == "__main__":
    # Example usage
    import argparse

    parser = argparse.ArgumentParser(description="Build corpus from configuration")
    parser.add_argument("--config", required=True, help="Path to corpus configuration YAML")
    parser.add_argument("--mode", default="cpu", choices=["cpu", "gpu"], help="Processing mode")
    args = parser.parse_args()

    async def main():
        async def progress_callback(progress):
            print(f"Progress: {progress['percentage']:.1f}% - {progress.get('current_document', '')}")

        results = await build_corpus_from_config(
            args.config,
            args.mode,
            progress_callback
        )
        print(f"Build complete: {results}")

    asyncio.run(main())