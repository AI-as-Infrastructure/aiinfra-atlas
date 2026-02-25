"""
Universal corpus builder for ATLAS.

Config-driven corpus store creation that replaces hardcoded corpus-specific logic
with a flexible system that can handle any corpus structure.
"""

import json
import yaml
import hashlib
import asyncio
import logging
import time
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


class ChromaEmbeddingFunction:
    """Wrapper to make LangChain embeddings compatible with ChromaDB."""

    def __init__(self, langchain_embeddings):
        self.embeddings = langchain_embeddings

    def __call__(self, input: List[str]) -> List[List[float]]:
        """Embed a list of texts and return embeddings."""
        # Use the LangChain embeddings to generate embeddings
        return self.embeddings.embed_documents(input)


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
        self.actual_mode = mode  # Track actual mode after any fallback
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

    def _clean_existing_corpus(self):
        """Clean up existing corpus files for a fresh rebuild."""
        import shutil

        # Since we're now building in a temp directory, just clean that directory
        # No need to worry about ChromaDB connections since we start fresh
        items_to_clean = [
            self.output_dir / "chroma_db",  # ChromaDB vector store
            self.output_dir / "manifest.json",  # Corpus manifest
            self.output_dir / "bm25_corpus.jsonl",  # BM25 corpus
            self.output_dir / "tmp",  # Temporary files
        ]

        for item in items_to_clean:
            if item.exists():
                try:
                    if item.is_dir():
                        logger.info(f"Removing existing directory: {item}")
                        shutil.rmtree(item)
                    else:
                        logger.info(f"Removing existing file: {item}")
                        item.unlink()
                except Exception as e:
                    logger.warning(f"Failed to remove {item}: {e}")

        logger.info("Build directory cleanup completed")

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

        # Track build timing
        build_start_time = time.monotonic()

        # Clean up existing corpus files for a fresh build
        self._clean_existing_corpus()

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
            await self._initialize_embeddings()

            # Step 4: Create vector store
            await self._create_vector_store()

            # Step 5: Generate manifest (with build timing)
            build_duration = round(time.monotonic() - build_start_time, 1)
            manifest_path = self._generate_manifest(build_duration_seconds=build_duration)

            # Step 6: Generate BM25 corpus
            bm25_path = await self._generate_bm25_corpus()

            # Step 7: Save configuration
            config_path = self._save_config()

            # Step 8: Generate corpus adapter from template
            adapter_path = self._generate_corpus_adapter()

            # Clean up checkpoint on success
            self.progress_tracker.cleanup_checkpoint()

            # Calculate vector store size
            vector_store_path = self.output_dir / "chroma_db"
            vector_store_size = 0
            if vector_store_path.exists():
                for item in vector_store_path.rglob("*"):
                    if item.is_file():
                        vector_store_size += item.stat().st_size

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
                "adapter_path": str(adapter_path),
                "collection_name": self.collection_name,  # Include the actual collection name used
                "documents_processed": len(self.documents),
                "vector_store_size": vector_store_size,
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
            # Use sparse_checkout paths if available
            path = ""
            if self.config.source.sparse_checkout and len(self.config.source.sparse_checkout) > 0:
                path = self.config.source.sparse_checkout[0]  # Use first path
            return github_manager.fetch_corpus(
                repo_url=self.config.source.location,
                branch=self.config.source.branch or "main",
                path=path
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
            elif file_type == "xml" and self._is_tei_workflow():
                # TEI-XML workflow: use TEI parser and chunking
                docs = self._load_tei_documents(source_path)
                all_docs.extend(docs)
                logger.info(f"Loaded {len(docs)} TEI-XML documents via TEI pipeline")
                continue
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

    def _is_tei_workflow(self) -> bool:
        """Check if TEI-XML workflow is enabled in config."""
        return (
            hasattr(self.config, 'tei_workflow')
            and self.config.tei_workflow is not None
            and self.config.tei_workflow.enabled
        )

    def _load_tei_documents(self, source_path: Path) -> List[Document]:
        """Load and chunk TEI-XML documents using the TEI pipeline.

        Uses tei_xml_parser and tei_chunking instead of UnstructuredXMLLoader.
        Returns pre-chunked Documents with TEI metadata already applied.
        """
        from backend.modules.tei_chunking import chunk_tei_corpus

        tei_config = self.config.tei_workflow

        # Build metadata mappings dict from config
        metadata_mappings = None
        if tei_config.metadata_mappings:
            metadata_mappings = {
                m.tei_field: m.role for m in tei_config.metadata_mappings
            }

        # Determine filter info for backward compatibility
        corpus_name = self.config.metadata.name
        filter_id = corpus_name
        filter_label = self.config.metadata.display_name

        # If we have filters configured, use the first non-"all" filter
        if self.config.filters.filters:
            for f in self.config.filters.filters:
                if f.id != "all":
                    filter_id = f.id
                    filter_label = f.label
                    break

        docs = chunk_tei_corpus(
            directory=source_path,
            strategy=tei_config.chunking_strategy,
            chunk_size=self.config.embedding.chunk_size,
            chunk_overlap=self.config.embedding.chunk_overlap,
            corpus_name=corpus_name,
            filter_id=filter_id,
            filter_label=filter_label,
            metadata_mappings=metadata_mappings,
            selected_fields=tei_config.selected_fields or None,
        )

        logger.info(f"TEI pipeline produced {len(docs)} chunks from source directory")
        return docs

    def _build_facets_from_tei(self) -> List[Dict[str, Any]]:
        """Build facets array from TEI workflow configuration and document metadata.

        Analyzes built documents to discover unique values, min/max dates,
        and populates the facets array for the manifest.
        """
        if not self._is_tei_workflow():
            return []

        tei_config = self.config.tei_workflow
        facets = []

        # If explicit facets are configured, use them
        if tei_config.facets:
            for facet_cfg in tei_config.facets:
                facet = {
                    "field": facet_cfg.field,
                    "label": facet_cfg.label,
                    "type": facet_cfg.type,
                }
                # Collect values/ranges from documents
                self._populate_facet_values(facet)
                facets.append(facet)
        else:
            # Auto-generate facets from common TEI fields present in documents
            facets = self._auto_discover_facets()

        return facets

    def _populate_facet_values(self, facet: Dict[str, Any]) -> None:
        """Populate a facet with values/ranges from built documents."""
        field = facet["field"]
        facet_type = facet["type"]

        values = set()
        for doc in self.documents:
            val = doc.metadata.get(field)
            if val:
                values.add(str(val))

        if facet_type == "date_range" and values:
            # Extract min/max dates
            sorted_dates = sorted(values)
            facet["min"] = sorted_dates[0]
            facet["max"] = sorted_dates[-1]
            facet["count"] = len(values)
        elif facet_type == "keyword" and values:
            # For keywords, split semicolon-separated values
            all_keywords = set()
            for v in values:
                for kw in v.split(";"):
                    kw = kw.strip()
                    if kw:
                        all_keywords.add(kw)
            facet["values"] = sorted(all_keywords)
        elif facet_type == "text" and values:
            facet["values"] = sorted(values)

    def _auto_discover_facets(self) -> List[Dict[str, Any]]:
        """Auto-discover facets from TEI metadata present in documents."""
        if not self.documents:
            return []

        # Check which TEI fields have values across documents
        field_configs = {
            "tei_sender": ("Sender", "text"),
            "tei_recipient": ("Recipient", "text"),
            "tei_date": ("Date", "date_range"),
            "tei_place": ("Place", "text"),
            "tei_keywords": ("Keywords", "keyword"),
        }

        facets = []
        for field, (label, facet_type) in field_configs.items():
            # Count docs with this field
            count = sum(1 for d in self.documents if d.metadata.get(field))
            if count == 0:
                continue

            facet = {"field": field, "label": label, "type": facet_type}
            self._populate_facet_values(facet)
            facets.append(facet)

        return facets

    def _match_document_to_filter(self, doc: Document) -> Optional[FilterDefinition]:
        """Match document to appropriate filter based on patterns."""
        import fnmatch
        import re

        # Skip "all" filter and try to match specific corpus filters first
        non_all_filters = [f for f in self.config.filters.filters if f.type != "all" and f.id != "all"]
        all_filter = next((f for f in self.config.filters.filters if f.type == "all" or f.id == "all"), None)

        # First, try to match against specific corpus filters
        for filter_def in non_all_filters:
            # Check pattern match
            if filter_def.pattern:
                source_path = doc.metadata.get("source", "")

                # For corpus filters, check if the path contains the corpus directory name
                # e.g., for "United Kingdom", check if path contains "United Kingdom" or "United_Kingdom"
                if filter_def.label:
                    # Normalize label to handle spaces and underscores
                    label_variations = [
                        filter_def.label,
                        filter_def.label.replace(" ", "_"),
                        filter_def.label.replace("_", " ")
                    ]
                    for variant in label_variations:
                        if variant in source_path:
                            logger.debug(f"Matched document to corpus '{filter_def.label}' by path: {source_path}")
                            return filter_def

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

        # If no specific filter matched and we have an "all" filter, use it as fallback
        # But tag it with the actual corpus from the path if possible
        if all_filter:
            source_path = doc.metadata.get("source", "")
            # Try to extract corpus name from path
            if "Australia" in source_path:
                # Create a virtual filter for Australia
                return FilterDefinition(
                    id="australia",
                    label="Australia",
                    type="directory",
                    pattern=None
                )
            elif "New_Zealand" in source_path or "New Zealand" in source_path:
                # Create a virtual filter for New Zealand
                return FilterDefinition(
                    id="new_zealand",
                    label="New Zealand",
                    type="directory",
                    pattern=None
                )
            elif "United_Kingdom" in source_path or "United Kingdom" in source_path:
                # Create a virtual filter for United Kingdom
                return FilterDefinition(
                    id="united_kingdom",
                    label="United Kingdom",
                    type="directory",
                    pattern=None
                )
            # Fall back to all filter if no corpus detected
            return all_filter

        # Default filter if exists
        return self.config.filters.filters[0] if self.config.filters.filters else None

    async def _initialize_embeddings(self):
        """Initialize embedding model."""
        logger.info(f"Initializing embeddings: {self.config.embedding.model_id}")

        device = "cuda" if self.mode == "gpu" and torch.cuda.is_available() else "cpu"
        self.actual_mode = device  # Track actual mode from the start

        # Log GPU information if available
        if device == "cuda":
            logger.info(f"🚀 Attempting GPU acceleration for embeddings")
            logger.info(f"   Detected GPU: {torch.cuda.get_device_name(0)}")
            # Check compute capability for newer GPUs
            major, minor = torch.cuda.get_device_capability(0)
            logger.info(f"   Compute capability: {major}.{minor}")
            if major >= 12:
                logger.info(f"   ⚠️  RTX 50 series detected - PyTorch may not support this yet")
                logger.info(f"   Will fall back to CPU if GPU operations fail")
            elif major >= 9:
                logger.info(f"   Note: Newer GPU architecture detected (RTX 40/50 series)")
        else:
            logger.info(f"💻 Using CPU for embeddings (no GPU detected)")

        # Use the centralized embeddings module which handles GPU detection and fallback
        from backend.modules.embeddings import get_embeddings_model

        try:
            self.embeddings = get_embeddings_model(
                model_name=self.config.embedding.model_id,
                config={"embedding_model": self.config.embedding.model_id}
            )

            # Test if embeddings actually work on the selected device
            test_texts = ["test sentence one", "test sentence two", "test sentence three"]
            _ = self.embeddings.embed_documents(test_texts)

            # The centralized module may have fallen back to CPU, so check actual device
            # Get the actual device being used
            if hasattr(self.embeddings, 'client') and hasattr(self.embeddings.client, 'device'):
                actual_device = str(self.embeddings.client.device)
                if 'cuda' in actual_device:
                    self.actual_mode = "gpu"
                    logger.info(f"✅ SUCCESS: Embeddings running on GPU")
                    logger.info(f"   Build will use GPU acceleration")
                else:
                    self.actual_mode = "cpu"
                    if device == "cuda":
                        logger.warning(f"⚠️  FALLBACK: GPU requested but embeddings running on CPU")
                        logger.info(f"   Build will continue using CPU (slower but stable)")
                    else:
                        logger.info(f"✅ SUCCESS: Embeddings running on CPU")
            else:
                # If we can't determine device, assume it matches what was requested
                logger.info(f"✅ Embeddings initialized on {device.upper()}")

        except Exception as e:
            logger.error(f"Failed to initialize embeddings: {e}")
            # If GPU fails, actual_mode should reflect CPU
            if "CUDA" in str(e) or "no kernel image" in str(e):
                self.actual_mode = "cpu"
                logger.error(f"❌ GPU initialization failed (PyTorch compatibility issue)")
                logger.info(f"   This typically means your GPU is too new for current PyTorch")
                logger.info(f"   System will use CPU mode instead")
            raise

        # Send progress update with actual mode if there's a callback
        if self.progress_tracker and self.progress_tracker.callback:
            await self.progress_tracker.callback({
                "status": "building",
                "percentage": 10,
                "message": f"Embeddings initialized on {self.actual_mode.upper()}",
                "actual_mode": self.actual_mode
            })

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
                    progress["actual_mode"] = self.actual_mode  # Add actual mode to progress
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
        if not self.config.metadata.name:
            raise ValueError("Corpus name is required but was not provided")

        # Process the name: lowercase, replace spaces and hyphens with underscores
        raw_name = self.config.metadata.name.lower().replace(" ", "_").replace("-", "_")

        # Ensure the collection name meets ChromaDB requirements
        # Must be 3-63 chars, start and end with alphanumeric
        if len(raw_name) < 3:
            collection_name = f"corpus_{raw_name}"
        elif len(raw_name) > 63:
            collection_name = raw_name[:63]
        else:
            collection_name = raw_name

        # Ensure it starts and ends with alphanumeric
        import re
        if not re.match(r'^[a-zA-Z0-9]', collection_name):
            collection_name = f"c_{collection_name}"
        if not re.match(r'[a-zA-Z0-9]$', collection_name):
            collection_name = f"{collection_name}_c"

        # Final validation
        if not re.match(r'^[a-zA-Z0-9][a-zA-Z0-9._-]*[a-zA-Z0-9]$', collection_name):
            raise ValueError(f"Invalid collection name after processing: {collection_name}")

        logger.info(f"Using collection name: {collection_name}")

        # Store collection name for use in manifest
        self.collection_name = collection_name

        # Batch process embeddings to avoid blocking
        logger.info(f"Creating vector store with {len(all_chunks)} chunks in batches...")
        batch_size = 100  # Process 100 chunks at a time

        # Initialize Chroma persistent client
        import chromadb
        from chromadb.config import Settings

        # Create a fresh client (directory should be clean from _clean_existing_corpus)
        client = chromadb.PersistentClient(
            path=str(persist_dir),
            settings=Settings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )

        logger.info(f"Initialized ChromaDB client at {persist_dir}")

        # Wrap LangChain embeddings for ChromaDB compatibility
        chroma_embeddings = ChromaEmbeddingFunction(self.embeddings)

        # Try to create collection (should be fresh after reset)
        try:
            collection = client.create_collection(
                name=collection_name,
                embedding_function=chroma_embeddings
            )
            logger.info(f"Created new collection: {collection_name}")
        except Exception as e:
            logger.error(f"Failed to create collection {collection_name}: {e}")
            # Try to get existing collection as fallback
            try:
                logger.info(f"Attempting to get existing collection: {collection_name}")
                collection = client.get_collection(
                    name=collection_name,
                    embedding_function=chroma_embeddings
                )
                logger.info(f"Using existing collection: {collection_name}")
            except Exception as get_error:
                logger.error(f"Failed to get existing collection: {get_error}")
                raise ValueError(f"Cannot create or get ChromaDB collection: {get_error}")

        # Process in batches
        for i in range(0, len(all_chunks), batch_size):
            batch = all_chunks[i:i+batch_size]
            batch_end = min(i+batch_size, len(all_chunks))

            # Update progress
            progress_pct = 50 + (40 * batch_end / len(all_chunks))  # 50-90% range
            if self.progress_tracker.callback:
                await self.progress_tracker.callback({
                    "status": "building",
                    "percentage": progress_pct,
                    "processed_documents": len(self.documents),
                    "total_documents": len(self.documents),
                    "current_document": f"Processing embeddings batch {i//batch_size + 1}/{(len(all_chunks) + batch_size - 1)//batch_size}",
                    "message": f"Generating embeddings ({batch_end}/{len(all_chunks)} chunks)"
                })

            # Pre-compute embeddings for this batch to avoid blocking
            batch_texts = [doc.page_content for doc in batch]
            logger.info(f"Computing embeddings for batch {i//batch_size + 1}")
            batch_embeddings = self.embeddings.embed_documents(batch_texts)

            # Add documents to collection with pre-computed embeddings
            collection.add(
                ids=[doc.metadata.get("chunk_id", f"chunk_{i+j}") for j, doc in enumerate(batch)],
                documents=batch_texts,
                metadatas=[doc.metadata for doc in batch],
                embeddings=batch_embeddings
            )

            # Small async sleep to allow other tasks
            await asyncio.sleep(0.1)

            logger.debug(f"Added batch {i//batch_size + 1} to collection")

        # Verify collection has data
        try:
            count = collection.count()
            logger.info(f"Collection {collection_name} now contains {count} vectors")

            if count == 0:
                raise ValueError("Collection is empty after adding documents!")
        except Exception as e:
            logger.error(f"Error verifying collection: {e}")

        # Create Chroma vector store wrapper with persist directory
        from langchain_community.vectorstores import Chroma
        self.vector_store = Chroma(
            client=client,
            collection_name=collection_name,
            embedding_function=self.embeddings,
            persist_directory=str(persist_dir)
        )

        # Note: ChromaDB PersistentClient auto-persists, no need to call persist()
        # Verify files were created
        chroma_files = list(persist_dir.glob("*"))
        logger.info(f"ChromaDB files created: {len(chroma_files)} files in {persist_dir}")
        for file in chroma_files[:5]:  # Log first 5 files
            logger.debug(f"  - {file.name}")

        logger.info(f"Vector store created and auto-persisted to {persist_dir}")

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
        chunk_size = self.config.embedding.chunk_size or 1500
        chunk_overlap = self.config.embedding.chunk_overlap or 150
        splitter_type = getattr(self.config.embedding, 'text_splitter_type', 'RecursiveCharacterTextSplitter')

        if splitter_type == 'RecursiveCharacterTextSplitter':
            return RecursiveCharacterTextSplitter(
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
                length_function=len
            )
        elif splitter_type == 'CharacterTextSplitter':
            return CharacterTextSplitter(
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
                length_function=len
            )
        elif splitter_type == 'TokenTextSplitter':
            # For token-based splitting, we can use RecursiveCharacterTextSplitter with different separators
            return RecursiveCharacterTextSplitter(
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
                length_function=len,
                separators=["\n\n", "\n", " ", ""]
            )
        elif splitter_type == 'SentenceTextSplitter':
            # For sentence-based splitting
            return RecursiveCharacterTextSplitter(
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
                length_function=len,
                separators=[".", "!", "?", "\n\n", "\n", " ", ""]
            )
        else:
            # Default to RecursiveCharacterTextSplitter
            logger.warning(f"Unknown text splitter type: {splitter_type}, using RecursiveCharacterTextSplitter")
            return RecursiveCharacterTextSplitter(
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
                length_function=len
            )

    def _collect_build_info(self, build_duration_seconds: Optional[float] = None) -> Dict[str, Any]:
        """Collect build environment info for manifest reproducibility."""
        try:
            sys_info = SystemRequirementsChecker.get_system_info()
        except Exception as e:
            logger.warning(f"Failed to collect system info for build metadata: {e}")
            sys_info = {}

        gpu_info = sys_info.get("gpu", {})
        gpu_available = gpu_info.get("available", False)
        actual_mode = getattr(self, 'actual_mode', self.mode)

        return {
            "mode": actual_mode,
            "duration_seconds": build_duration_seconds,
            "python_version": sys_info.get("platform", {}).get("python_version"),
            "pytorch_version": sys_info.get("pytorch", {}).get("version"),
            "cuda_version": sys_info.get("pytorch", {}).get("cuda_version"),
            "platform": f"{sys_info.get('platform', {}).get('system', '')} {sys_info.get('platform', {}).get('release', '')}".strip() or None,
            "machine": sys_info.get("platform", {}).get("machine"),
            "gpu_name": gpu_info.get("name") if gpu_available else None,
            "gpu_memory_gb": round(gpu_info.get("memory_gb", 0), 1) if gpu_available and gpu_info.get("memory_gb") else None,
            "gpu_used": actual_mode == "gpu" and gpu_available,
            "cpu_cores": sys_info.get("cpu", {}).get("cores"),
            "system_ram_gb": round(sys_info.get("memory", {}).get("total_gb", 0), 1) if sys_info.get("memory", {}).get("total_gb") else None,
            "builder_version": "1.4"
        }

    def _generate_manifest(self, build_duration_seconds: Optional[float] = None) -> Path:
        """Generate manifest.json with corpus metadata and build environment."""
        logger.info("Generating manifest...")

        # Calculate statistics
        stats = {
            "total_documents": len(self.documents),
            "total_chunks": self.vector_store._collection.count() if self.vector_store else 0,
            "filters": {}
        }

        for filter_id, progress in self.progress_tracker.filter_progress.items():
            stats["filters"][filter_id] = progress

        # Get filter information for ALL filters
        filters_info = {}

        # Collect unique filter values from documents
        if self.documents and self.config.filters:
            # Initialize value sets for each filter
            filter_values = {}
            for filter_def in self.config.filters.filters:
                filter_values[filter_def.id] = set()

            # Collect values from documents
            for doc in self.documents:
                metadata = doc.metadata
                for filter_def in self.config.filters.filters:
                    filter_id = filter_def.id
                    if filter_id in metadata:
                        filter_values[filter_id].add(metadata[filter_id])

            # Build filter info dictionary
            for i, filter_def in enumerate(self.config.filters.filters, 1):
                filter_key = f"filter_{i}"
                filters_info[filter_key] = {
                    "id": filter_def.id,
                    "label": filter_def.label or filter_def.id,
                    "type": filter_def.type if hasattr(filter_def, 'type') else "directory",
                    "pattern": filter_def.pattern if hasattr(filter_def, 'pattern') else None,
                    "values": sorted(list(filter_values[filter_def.id]))
                }

        # For backward compatibility, also set filter_1 and filter_2
        filter_1_info = filters_info.get("filter_1")
        filter_2_info = filters_info.get("filter_2")

        # Capture build environment for reproducibility
        build_info = self._collect_build_info(build_duration_seconds)

        # Build facets array for TEI corpora (v1.5)
        facets = self._build_facets_from_tei() if self._is_tei_workflow() else []

        # Create manifest with enhanced embedding documentation
        manifest = {
            "version": "1.5" if facets else "1.4",
            "created": datetime.now().isoformat(),
            "corpus_name": self.config.metadata.name,
            "metadata": self.config.metadata.dict(),
            "source": self.config.source.dict(),
            # Inter-rater configuration (defaults to disabled)
            "inter_rater": self.config.inter_rater.dict() if self.config.inter_rater else {
                "enabled": False,
                "max_ratings": 3,
                "sessions_per_user": 5
            },
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
                "collection_name": getattr(self, 'collection_name', self.config.metadata.name.lower().replace(" ", "_")),
                "persist_directory": str(self.output_dir / "chroma_db")
            },
            "filters": filters_info,
            "facets": facets,
            "statistics": stats,
            "fields": {
                "corpus": {
                    "type": "enum",
                    "values": [filter_def.id for filter_def in (self.config.filters.filters if self.config.filters else [])]
                }
            },
            "build": build_info
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

        # Convert config to dict and handle datetime objects
        config_data = self.config.dict()
        if 'created_at' in config_data:
            config_data['created_at'] = config_data['created_at'].isoformat()
        if 'last_modified' in config_data:
            config_data['last_modified'] = config_data['last_modified'].isoformat()

        # Save to YAML
        with open(config_path, 'w') as f:
            yaml.dump(config_data, f, default_flow_style=False, sort_keys=False)

        logger.info(f"Configuration saved to {config_path}")
        return config_path

    def _generate_corpus_adapter(self) -> Path:
        """Generate corpus-specific adapter from template."""
        logger.info("Generating corpus-specific adapter...")

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
            embedding_model=self.config.embedding.model_id,
            collection_name=self.collection_name  # Use the actual collection name from vector store creation
        )

        # Save corpus adapter
        adapter_name = f"{corpus_name.replace('-', '_')}_adapter.py"
        adapter_path = self.output_dir / adapter_name

        with open(adapter_path, 'w') as f:
            f.write(retriever_code)

        logger.info(f"Corpus adapter generated: {adapter_path}")
        return adapter_path


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