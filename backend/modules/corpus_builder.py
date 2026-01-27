"""
Universal corpus builder for ATLAS.

Config-driven corpus store creation that replaces hardcoded corpus-specific logic
with a flexible system that can handle any corpus structure.
"""

import json
import hashlib
import asyncio
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime

import torch
from langchain.text_splitter import RecursiveCharacterTextSplitter, CharacterTextSplitter
from langchain_community.document_loaders import DirectoryLoader, TextLoader, UnstructuredXMLLoader
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain.schema import Document

from backend.modules.corpus_config import CorpusConfig, FilterDefinition
from backend.modules.github_corpus import GitHubCorpusManager
from backend.modules.build_progress import BuildProgressTracker
from backend.modules.system_requirements import SystemRequirementsChecker
from backend.modules.metadata_extractor import MetadataExtractor
from backend.modules.url_builder import URLBuilder

logger = logging.getLogger(__name__)


class UniversalCorpusBuilder:
    """Universal corpus builder that uses configuration to build any corpus."""

    def __init__(self, config: CorpusConfig, mode: str = "cpu", output_dir: Optional[Path] = None):
        """
        Initialize corpus builder.

        Args:
            config: Corpus configuration
            mode: Processing mode ('cpu' or 'gpu')
            output_dir: Output directory (default: backend/corpus/tmp)
        """
        self.config = config
        self.mode = mode
        self.progress_tracker = None
        self.documents = []
        self.vector_store = None
        self.embeddings = None

        # Allow configurable output directory
        if output_dir is None:
            output_dir = Path("backend/corpus/tmp")
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Initialize metadata extractor and URL builder
        # Get extraction settings from citation config or source config
        date_regex = None
        extract_inline_urls = False

        # Check if we have date extraction pattern in source config or citation config
        if hasattr(self.config.source, 'custom_date_pattern') and self.config.source.custom_date_pattern:
            date_regex = self.config.source.custom_date_pattern
        elif hasattr(self.config.citation, 'metadata_patterns') and self.config.citation.metadata_patterns:
            date_regex = self.config.citation.metadata_patterns.get('date')

        # Check source config for extraction settings
        if hasattr(self.config.source, 'extract_inline_urls'):
            extract_inline_urls = self.config.source.extract_inline_urls

        self.metadata_extractor = MetadataExtractor(
            filename_pattern=None,  # We're not using template patterns for now
            extract_inline_urls=extract_inline_urls,
            date_regex=date_regex
        )

        # URL builder from citation config
        url_template = None
        if hasattr(self.config.citation, 'url_pattern'):
            url_template = self.config.citation.url_pattern

        self.url_builder = URLBuilder(url_template)

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
        self.progress_tracker = BuildProgressTracker(
            callback=progress_callback,
            checkpoint_dir=self.output_dir
        )

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

            # Step 8: Generate retriever from template
            retriever_path = self._generate_retriever()

            # Clean up checkpoint on success
            self.progress_tracker.cleanup_checkpoint()

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
                "retriever_path": str(retriever_path),
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

        # Update progress to show we're starting
        if self.progress_tracker.callback:
            await self.progress_tracker.callback({
                "status": "building",
                "percentage": 0,
                "processed_documents": 0,
                "total_documents": 0,
                "current_document": "Scanning for documents...",
                "message": "Loading documents from source directory"
            })

        all_docs = []

        # Handle file_extensions from SourceConfig
        file_extensions = self.config.source.file_extensions or ".txt"
        # Convert string like ".txt" or ".txt,.xml" to list of extensions
        if isinstance(file_extensions, str):
            # Remove dots and split by comma
            extensions = [ext.strip().lstrip('.') for ext in file_extensions.split(',')]
        else:
            extensions = file_extensions

        for file_type in extensions:
            logger.info(f"Loading {file_type} files...")

            if file_type == "txt":
                loader = DirectoryLoader(
                    str(source_path),
                    glob=f"**/*.{file_type}" if self.config.source.include_subdirectories else f"*.{file_type}",
                    loader_cls=TextLoader,
                    loader_kwargs={"encoding": "utf-8", "autodetect_encoding": True}
                )
            elif file_type == "xml":
                loader = DirectoryLoader(
                    str(source_path),
                    glob=f"**/*.{file_type}" if self.config.source.include_subdirectories else f"*.{file_type}",
                    loader_cls=UnstructuredXMLLoader,
                    loader_kwargs={"encoding": "utf-8"}
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
                self.progress_tracker.add_error(f"Failed to load {file_type} files: {e}")

        logger.info(f"Total documents loaded: {len(all_docs)}")

        # Apply filters if configured
        if self.config.filters:
            all_docs = self._apply_filters(all_docs)

        self.documents = all_docs
        self.progress_tracker.total_docs = len(self.documents)

        # Update progress with document count
        if self.progress_tracker.callback:
            await self.progress_tracker.callback({
                "status": "building",
                "percentage": 5,
                "processed_documents": 0,
                "total_documents": len(self.documents),
                "current_document": f"Loaded {len(self.documents)} documents",
                "message": f"Documents loaded successfully: {len(self.documents)} files"
            })

    def _apply_filters(self, documents: List[Document]) -> List[Document]:
        """Apply configured filters and enrich with comprehensive metadata."""
        if not self.config.filters:
            return documents

        filtered_docs = []
        for doc in documents:
            matched_filter = self._match_document_to_filter(doc)
            if matched_filter:
                # Get source filename
                source_path = doc.metadata.get("source", "")
                filename = Path(source_path).name

                # Core metadata (always present)
                doc.metadata["source_filename"] = filename
                doc.metadata["filter_1"] = matched_filter.id
                doc.metadata["corpus"] = matched_filter.id  # Legacy compatibility
                doc.metadata["corpus_label"] = matched_filter.label

                # Extract custom metadata from filename
                extracted = self.metadata_extractor.extract_from_filename(filename)
                doc.metadata.update(extracted)

                # Extract inline URL from content if configured
                inline_url, cleaned_content = self.metadata_extractor.extract_inline_url(doc.page_content)
                if inline_url:
                    doc.metadata["source_url"] = inline_url
                    doc.page_content = cleaned_content  # Remove URL line from content
                    logger.debug(f"Extracted inline URL for {filename}: {inline_url}")
                elif self.url_builder.template:
                    # Fallback to template-generated URL if no inline URL found
                    source_url = self.url_builder.build_url(**extracted)
                    if source_url:
                        doc.metadata["source_url"] = source_url

                filtered_docs.append(doc)

        logger.info(f"Filtered {len(documents)} documents to {len(filtered_docs)}")
        return filtered_docs

    def _match_document_to_filter(self, doc: Document) -> Optional[FilterDefinition]:
        """Match document to appropriate filter based on patterns."""
        import fnmatch
        import re

        for filter_def in self.config.filters.filters:
            # Check pattern match
            if filter_def.pattern:
                source_path = doc.metadata.get("source", "")

                # If pattern looks like a glob pattern (contains * or ?), use fnmatch
                if '*' in filter_def.pattern or '?' in filter_def.pattern:
                    # Convert glob to work with full path matching
                    if fnmatch.fnmatch(source_path, filter_def.pattern):
                        return filter_def
                else:
                    # Otherwise try as regex
                    try:
                        if re.search(filter_def.pattern, source_path):
                            return filter_def
                    except re.error:
                        # Invalid regex, skip this filter
                        logger.warning(f"Invalid regex pattern: {filter_def.pattern}")

            # Check metadata field match
            if hasattr(filter_def, 'metadata_field') and hasattr(filter_def, 'metadata_value'):
                if filter_def.metadata_field and filter_def.metadata_value:
                    if doc.metadata.get(filter_def.metadata_field) == filter_def.metadata_value:
                        return filter_def

        # Default filter if exists
        return self.config.filters.filters[0] if self.config.filters.filters else None

    def _initialize_embeddings(self):
        """Initialize embedding model."""
        logger.info(f"Initializing embeddings: {self.config.embedding.model_id}")

        device = "cuda" if self.mode == "gpu" and torch.cuda.is_available() else "cpu"

        model_kwargs = {"device": device}
        if device == "cuda":
            model_kwargs["trust_remote_code"] = True

        encode_kwargs = {
            "normalize_embeddings": True,
            "batch_size": self.config.embedding.batch_size
        }

        self.embeddings = HuggingFaceEmbeddings(
            model_name=self.config.embedding.model_id,
            model_kwargs=model_kwargs,
            encode_kwargs=encode_kwargs
        )

        logger.info(f"Embeddings initialized on {device}")

    async def _create_vector_store(self):
        """Create vector store with documents."""
        logger.info("Creating vector store...")

        # Send initial progress update
        if self.progress_tracker.callback:
            await self.progress_tracker.callback({
                "status": "building",
                "percentage": 15,
                "processed_documents": 0,
                "total_documents": len(self.documents),
                "current_document": "Starting document processing...",
                "message": "Preparing to create vector store"
            })

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

                # Add chunk-specific metadata
                filename = doc.metadata.get("source_filename", f"doc_{i}")
                parent_id = Path(filename).stem

                for chunk_idx, chunk in enumerate(chunks):
                    # Unique chunk ID
                    chunk.metadata["chunk_id"] = f"{parent_id}_chunk_{chunk_idx}"
                    chunk.metadata["chunk_index"] = chunk_idx
                    chunk.metadata["parent_doc_id"] = parent_id
                    chunk.metadata["total_chunks"] = len(chunks)

                all_chunks.extend(chunks)
            except Exception as e:
                logger.warning(f"Error splitting document: {e}")
                self.progress_tracker.add_warning(str(e))

            self.progress_tracker.increment_processed()

            # Send progress update every 5 documents or on last document
            if (i + 1) % 5 == 0 or (i + 1) == len(self.documents):
                if self.progress_tracker.callback:
                    progress = self.progress_tracker.get_progress()
                    progress["current_document"] = f"Processing document {i+1}/{len(self.documents)}"
                    await self.progress_tracker.callback(progress)

        logger.info(f"Created {len(all_chunks)} chunks from {len(self.documents)} documents")

        # Update progress for embedding phase
        if self.progress_tracker.callback:
            await self.progress_tracker.callback({
                "status": "building",
                "percentage": 50,
                "processed_documents": len(self.documents),
                "total_documents": len(self.documents),
                "current_document": f"Creating embeddings for {len(all_chunks)} chunks...",
                "message": "Generating vector embeddings"
            })

        # Create vector store
        persist_dir = self.output_dir / "chroma_db"
        persist_dir.mkdir(parents=True, exist_ok=True)

        # Generate collection name from metadata
        collection_name = self.config.metadata.name.lower().replace(" ", "_").replace("-", "_")

        self.vector_store = Chroma.from_documents(
            documents=all_chunks,
            embedding=self.embeddings,
            collection_name=collection_name,
            persist_directory=str(persist_dir)
        )

        # Persist the vector store
        self.vector_store.persist()
        logger.info(f"Vector store created and persisted to {persist_dir}")

        # Update progress
        if self.progress_tracker.callback:
            await self.progress_tracker.callback({
                "status": "building",
                "percentage": 75,
                "processed_documents": len(self.documents),
                "total_documents": len(self.documents),
                "current_document": "Vector store created successfully",
                "message": "Finalizing corpus build"
            })

    def _get_text_splitter(self):
        """Get appropriate text splitter based on configuration."""
        if self.config.embedding.chunk_size:
            return RecursiveCharacterTextSplitter(
                chunk_size=self.config.embedding.chunk_size,
                chunk_overlap=self.config.embedding.chunk_overlap,
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

        # Get filter information for 2-filter system
        filter_1_info = None
        filter_2_info = None
        if self.config.filters:
            if len(self.config.filters) >= 1:
                filter_1_info = {
                    "label": self.config.filters[0].label or self.config.filters[0].id,
                    "values": []  # Will be populated from actual documents
                }
            if len(self.config.filters) >= 2:
                filter_2_info = {
                    "label": self.config.filters[1].label or self.config.filters[1].id,
                    "values": []
                }

        # Create manifest with enhanced embedding documentation
        manifest = {
            "version": "1.2",
            "created": datetime.now().isoformat(),
            "corpus_name": self.config.metadata.name,
            "metadata": self.config.metadata.dict(),
            "source": self.config.source.dict(),
            "embedding_model": {
                "id": self.config.embedding.model_id,
                "source": "huggingface",
                "is_default": self.config.embedding.model_id == "sentence-transformers/all-mpnet-base-v2",
                "validated": True,
                "characteristics": {
                    "embedding_dim": 768 if "mpnet" in self.config.embedding.model_id else None,
                    "max_sequence_length": 512,
                    "model_size_mb": None  # Would need actual calculation
                }
            },
            "embeddings": self.config.embedding.dict(),  # Keep for compatibility
            "vector_store": {
                "type": "chromadb",
                "collection_name": self.config.metadata.name.lower().replace(" ", "_"),
                "persist_directory": str(self.output_dir / "chroma_db")
            },
            "filters": {
                "filter_1": filter_1_info,
                "filter_2": filter_2_info
            },
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

    def _generate_retriever(self) -> Path:
        """Generate corpus-specific retriever from template."""
        logger.info("Generating corpus-specific retriever...")

        # Read template
        template_path = Path(__file__).parent.parent / "retrievers" / "templates" / "corpus_retriever_template.py"
        if not template_path.exists():
            logger.warning(f"Retriever template not found at {template_path}")
            return None

        with open(template_path, 'r') as f:
            template = f.read()

        # Convert corpus name to PascalCase for class name
        corpus_name = self.config.metadata.name
        corpus_class = ''.join(word.capitalize() for word in corpus_name.replace('-', '_').split('_'))

        # Get filter labels
        filter_1_label = self.config.filters.filters[0].label if self.config.filters.filters else "Category"
        filter_2_label = self.config.filters.filters[1].label if len(self.config.filters.filters) > 1 else "Subcategory"

        # Replace template variables
        retriever_code = template.format(
            corpus_name=corpus_name,
            CorpusClass=corpus_class,
            creation_date=datetime.now().strftime("%Y-%m-%d"),
            creation_time=datetime.now().strftime("%H:%M:%S"),
            filter_1_label=filter_1_label,
            filter_2_label=filter_2_label,
            embedding_model=self.config.embedding.model_id
        )

        # Save retriever
        retriever_name = f"{corpus_name.replace('-', '_')}_retriever.py"
        retriever_path = self.output_dir / retriever_name

        with open(retriever_path, 'w') as f:
            f.write(retriever_code)

        logger.info(f"Retriever generated: {retriever_path}")
        return retriever_path


async def build_corpus_from_config(
    config_path: str,
    mode: str = "cpu",
    output_dir: Optional[str] = None,
    progress_callback: Optional[Callable] = None
) -> Dict[str, Any]:
    """
    Build corpus from configuration file.

    Args:
        config_path: Path to corpus configuration YAML
        mode: Processing mode ('cpu' or 'gpu')
        output_dir: Output directory (optional)
        progress_callback: Optional async callback for progress updates

    Returns:
        Build results
    """
    # Load configuration
    config = CorpusConfig.from_yaml(config_path)

    # Check system requirements
    checker = SystemRequirementsChecker()
    requirements = checker.check_requirements(1000, mode)  # Estimate

    if not requirements["can_proceed"]:
        raise RuntimeError(f"System requirements not met: {requirements['issues']}")

    # Build corpus
    builder = UniversalCorpusBuilder(config, mode, output_dir)
    return await builder.build(progress_callback)