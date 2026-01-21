"""
Corpus configuration management module.

Handles loading, validation, and management of corpus configurations
for the UI-driven corpus wizard.
"""

import os
import yaml
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime
from pydantic import BaseModel, Field, validator


class CorpusMetadata(BaseModel):
    """Metadata about a corpus for research tracking."""

    name: str = Field(..., description="Corpus name")
    description: Optional[str] = Field(None, description="Corpus description")
    created: datetime = Field(default_factory=datetime.now)
    created_by: str = Field(default="corpus_wizard_v1")

    # Time period
    time_period_from: Optional[int] = Field(None, description="Start year")
    time_period_to: Optional[int] = Field(None, description="End year")

    # Research metadata
    copyright_status: Optional[str] = Field(None, description="Copyright status")
    copyright_statement: Optional[str] = Field(None, description="Copyright statement")
    doi: Optional[str] = Field(None, description="Digital Object Identifier")
    citation: Optional[str] = Field(None, description="Preferred citation")

    # Entities
    people: List[str] = Field(default_factory=list, description="Key people")
    places: List[str] = Field(default_factory=list, description="Key places")
    topics: List[str] = Field(default_factory=list, description="Key topics")

    # Organization preferences
    organization_preferences: List[str] = Field(
        default_factory=list,
        description="Preferred organization methods"
    )

    @validator('time_period_to')
    def validate_time_period(cls, v, values):
        """Ensure time period is valid."""
        if v and 'time_period_from' in values:
            if values['time_period_from'] and v < values['time_period_from']:
                raise ValueError('End year must be after start year')
        return v


class CorpusSource(BaseModel):
    """Configuration for corpus source location."""

    type: str = Field(..., description="Source type: local or github")
    location: str = Field(..., description="Path or URL to corpus")
    branch: Optional[str] = Field("main", description="Git branch (for GitHub)")
    path: Optional[str] = Field("", description="Path within repository")
    file_types: List[str] = Field(
        default_factory=lambda: ["txt", "xml"],
        description="File types to include"
    )

    @validator('type')
    def validate_type(cls, v):
        """Ensure source type is valid."""
        if v not in ['local', 'github']:
            raise ValueError('Source type must be "local" or "github"')
        return v


class CorpusFilter(BaseModel):
    """Configuration for a corpus filter."""

    id: str = Field(..., description="Filter identifier")
    label: str = Field(..., description="Display label")
    pattern: Optional[str] = Field(None, description="File pattern")
    metadata_field: Optional[str] = Field(None, description="Metadata field to filter on")
    xpath: Optional[str] = Field(None, description="XPath for XML filtering")
    document_count: Optional[int] = Field(None, description="Number of matching documents")


class EmbeddingConfig(BaseModel):
    """Embedding model configuration."""

    model: str = Field(..., description="HuggingFace model ID")
    pooling: str = Field("mean", description="Pooling strategy")
    chunk_size: int = Field(1000, description="Chunk size in characters")
    chunk_overlap: int = Field(100, description="Overlap between chunks")
    batch_size: int = Field(100, description="Processing batch size")

    @validator('pooling')
    def validate_pooling(cls, v):
        """Ensure pooling strategy is valid."""
        valid_strategies = ['mean', 'max', 'cls', 'mean+max']
        if v not in valid_strategies:
            raise ValueError(f'Pooling must be one of: {valid_strategies}')
        return v


class VectorStoreConfig(BaseModel):
    """Vector store configuration."""

    type: str = Field("chromadb", description="Vector store type")
    collection_name: str = Field(..., description="Collection name")
    persist_directory: str = Field(
        "backend/targets/chroma_db",
        description="Storage directory"
    )


class SearchConfig(BaseModel):
    """Search configuration."""

    type: str = Field("hybrid", description="Search type: hybrid or vector")
    k_default: int = Field(10, description="Default number of results")
    large_single_corpus: int = Field(120, description="Pool size for single corpus")
    large_all_corpus: int = Field(80, description="Pool size for all corpora")
    test_query: Optional[str] = Field(None, description="Test query for validation")


class CorpusConfig(BaseModel):
    """Complete corpus configuration."""

    metadata: CorpusMetadata
    source: CorpusSource
    filters: List[CorpusFilter] = Field(default_factory=list)
    embeddings: EmbeddingConfig
    vector_store: VectorStoreConfig
    search: SearchConfig

    # Processing options
    processing_mode: Optional[str] = Field(None, description="cpu or gpu")

    @classmethod
    def from_yaml(cls, path: str) -> 'CorpusConfig':
        """Load configuration from YAML file."""
        with open(path, 'r') as f:
            data = yaml.safe_load(f)
        return cls(**data)

    def to_yaml(self, path: str) -> None:
        """Save configuration to YAML file."""
        with open(path, 'w') as f:
            yaml.dump(self.dict(), f, default_flow_style=False)

    def validate_sources(self) -> bool:
        """Validate that source locations exist and are accessible."""
        if self.source.type == 'local':
            path = Path(self.source.location)
            if not path.exists():
                raise ValueError(f"Local path does not exist: {self.source.location}")
            if not path.is_dir():
                raise ValueError(f"Local path is not a directory: {self.source.location}")

            # Check for at least one file of the specified types
            has_files = False
            for file_type in self.source.file_types:
                if list(path.rglob(f"*.{file_type}")):
                    has_files = True
                    break

            if not has_files:
                raise ValueError(
                    f"No files of types {self.source.file_types} found in {self.source.location}"
                )

        elif self.source.type == 'github':
            # Basic URL validation
            if not self.source.location.startswith(('http://', 'https://')):
                raise ValueError(f"Invalid GitHub URL: {self.source.location}")

        return True

    def estimate_build_time(self, doc_count: int, mode: str = 'cpu') -> Dict[str, Any]:
        """Estimate build time based on document count and mode."""
        # These are rough estimates, should be calibrated based on actual performance
        if mode == 'gpu':
            docs_per_second = 4.0
        else:
            docs_per_second = 1.2

        seconds = doc_count / docs_per_second

        return {
            'seconds': seconds,
            'minutes': seconds / 60,
            'formatted': self._format_duration(seconds),
            'confidence': 0.75,
            'mode': mode,
            'docs_per_second': docs_per_second
        }

    @staticmethod
    def _format_duration(seconds: float) -> str:
        """Format duration in human-readable format."""
        if seconds < 60:
            return f"{int(seconds)} seconds"
        elif seconds < 3600:
            minutes = int(seconds / 60)
            remaining_seconds = int(seconds % 60)
            return f"{minutes}m {remaining_seconds}s"
        else:
            hours = int(seconds / 3600)
            remaining_minutes = int((seconds % 3600) / 60)
            return f"{hours}h {remaining_minutes}m"


class CorpusConfigManager:
    """Manager for corpus configurations."""

    def __init__(self, config_dir: str = "corpus_configs"):
        """Initialize the config manager."""
        self.config_dir = Path(config_dir)
        self.config_dir.mkdir(exist_ok=True)

    def list_configs(self) -> List[str]:
        """List available corpus configurations."""
        configs = []
        for path in self.config_dir.glob("*.yaml"):
            configs.append(path.stem)
        return configs

    def load_config(self, name: str) -> CorpusConfig:
        """Load a corpus configuration by name."""
        path = self.config_dir / f"{name}.yaml"
        if not path.exists():
            raise ValueError(f"Configuration not found: {name}")
        return CorpusConfig.from_yaml(str(path))

    def save_config(self, config: CorpusConfig) -> str:
        """Save a corpus configuration."""
        # Generate filename from corpus name
        name = config.metadata.name.lower().replace(' ', '_')
        path = self.config_dir / f"{name}.yaml"
        config.to_yaml(str(path))
        return str(path)

    def create_default_configs(self) -> None:
        """Create default configuration templates."""
        # Hansard configuration
        hansard_config = CorpusConfig(
            metadata=CorpusMetadata(
                name="Parliamentary Hansards 1901",
                description="Parliamentary records from Australia, New Zealand, and United Kingdom",
                time_period_from=1901,
                time_period_to=1901,
                copyright_status="public_domain",
                topics=["parliament", "politics", "legislation"],
                organization_preferences=["by_region", "by_date"]
            ),
            source=CorpusSource(
                type="local",
                location="${HANSARD_SOURCES_ROOT:-hansard_sources_FULL_TXT}",
                file_types=["txt"]
            ),
            filters=[
                CorpusFilter(id="1901_au", label="Australia (1901)", pattern="**/AU/**/*.txt"),
                CorpusFilter(id="1901_nz", label="New Zealand (1901)", pattern="**/NZ/**/*.txt"),
                CorpusFilter(id="1901_uk", label="United Kingdom (1901)", pattern="**/UK/**/*.txt")
            ],
            embeddings=EmbeddingConfig(
                model="Livingwithmachines/bert_1890_1900",
                pooling="mean+max",
                chunk_size=1000,
                chunk_overlap=100
            ),
            vector_store=VectorStoreConfig(
                collection_name="hansard_1901"
            ),
            search=SearchConfig(
                type="hybrid",
                test_query="parliament"
            )
        )

        # Save default configs
        self.save_config(hansard_config)