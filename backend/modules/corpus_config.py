"""
Corpus configuration management module.
Handles loading, validation, and management of corpus configurations.
"""

import os
import yaml
from pathlib import Path
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field, validator
from datetime import datetime


class TimePeriod(BaseModel):
    """Time period for corpus dating."""
    start: int = Field(..., description="Start year")
    end: int = Field(..., description="End year")

    @validator('end')
    def end_after_start(cls, v, values):
        if 'start' in values and v < values['start']:
            raise ValueError('End year must be after start year')
        return v


class CorpusMetadata(BaseModel):
    """Metadata for corpus identification and citation."""
    name: str = Field(..., description="Corpus name")
    display_name: str = Field(..., description="Display name for UI")
    description: str = Field(..., description="Corpus description")
    version: str = Field(default="1.0.0", description="Corpus version")
    time_period: Optional[TimePeriod] = None
    copyright_status: Optional[str] = None
    copyright_statement: Optional[str] = None
    doi: Optional[str] = None
    source_repository: Optional[str] = None
    entities: Optional[List[str]] = Field(default_factory=list, description="Key entities (people, places, topics)")


class SourceConfig(BaseModel):
    """Configuration for corpus source location."""
    type: str = Field(..., pattern="^(local|github)$", description="Source type")
    location: str = Field(..., description="Path or URL to source")
    branch: Optional[str] = Field(default="main", description="Git branch for GitHub sources")
    sparse_checkout: Optional[List[str]] = Field(default_factory=list, description="Paths for sparse checkout")


class FilterDefinition(BaseModel):
    """Definition of a corpus filter."""
    id: str = Field(..., description="Unique filter ID")
    label: str = Field(..., description="Display label")
    pattern: str = Field(..., description="File pattern or XPath")
    type: str = Field(default="directory", pattern="^(directory|xml|combined)$")
    parent_id: Optional[str] = None
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)


class CitationConfig(BaseModel):
    """Configuration for citation generation."""
    template: str = Field(
        default="{author}. {title}. {date}. {source}.",
        description="Citation template with placeholders"
    )
    url_pattern: Optional[str] = Field(
        default=None,
        description="URL pattern with placeholders"
    )
    metadata_patterns: Optional[Dict[str, str]] = Field(
        default_factory=dict,
        description="Regex patterns for metadata extraction"
    )
    source_name: Optional[str] = None
    source_url: Optional[str] = None


class FilterConfig(BaseModel):
    """Configuration for filter discovery."""
    method: str = Field(default="directory", pattern="^(directory|xml)$")
    directory_depth: int = Field(default=1, ge=1, le=2)
    xml_entities: Optional[List[str]] = Field(default_factory=list)
    filters: List[FilterDefinition] = Field(default_factory=list)


class EmbeddingConfig(BaseModel):
    """Configuration for embedding model."""
    model_id: str = Field(
        default="sentence-transformers/all-MiniLM-L6-v2",
        description="HuggingFace model ID"
    )
    chunk_size: int = Field(default=500, description="Chunk size in tokens")
    chunk_overlap: int = Field(default=50, description="Overlap between chunks")
    batch_size: int = Field(default=32, description="Batch size for processing")


class ProcessingConfig(BaseModel):
    """Configuration for corpus processing."""
    mode: str = Field(default="cpu", pattern="^(cpu|gpu)$")
    max_workers: int = Field(default=4, ge=1)
    memory_limit_gb: Optional[float] = None
    sample_size: Optional[int] = Field(default=None, description="Sample size for validation")


class CorpusConfig(BaseModel):
    """Complete corpus configuration."""
    metadata: CorpusMetadata
    source: SourceConfig
    filters: FilterConfig
    citation: CitationConfig
    embedding: EmbeddingConfig
    processing: ProcessingConfig
    created_at: datetime = Field(default_factory=datetime.now)
    last_modified: datetime = Field(default_factory=datetime.now)

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class CorpusConfigManager:
    """Manager for corpus configurations."""

    def __init__(self, config_dir: str = "config"):
        self.config_dir = Path(config_dir)
        self.config_file = self.config_dir / "corpus.yaml"
        self.backup_dir = Path("corpus_backups")

    def load_config(self) -> Optional[CorpusConfig]:
        """Load corpus configuration from file."""
        if not self.config_file.exists():
            return None

        try:
            with open(self.config_file, 'r') as f:
                data = yaml.safe_load(f)
            return CorpusConfig(**data)
        except Exception as e:
            print(f"Error loading corpus config: {e}")
            return None

    def save_config(self, config: CorpusConfig) -> bool:
        """Save corpus configuration to file."""
        try:
            config.last_modified = datetime.now()
            data = config.dict()

            # Convert datetime objects to strings for YAML
            data['created_at'] = data['created_at'].isoformat()
            data['last_modified'] = data['last_modified'].isoformat()

            with open(self.config_file, 'w') as f:
                yaml.dump(data, f, default_flow_style=False, sort_keys=False)
            return True
        except Exception as e:
            print(f"Error saving corpus config: {e}")
            return False

    def backup_config(self, config: CorpusConfig) -> Optional[Path]:
        """Create a backup of the current configuration."""
        try:
            self.backup_dir.mkdir(exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_file = self.backup_dir / f"corpus_config_{timestamp}.yaml"

            data = config.dict()
            data['created_at'] = data['created_at'].isoformat()
            data['last_modified'] = data['last_modified'].isoformat()

            with open(backup_file, 'w') as f:
                yaml.dump(data, f, default_flow_style=False, sort_keys=False)

            return backup_file
        except Exception as e:
            print(f"Error backing up config: {e}")
            return None

    def validate_config(self, config_dict: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """Validate a configuration dictionary."""
        try:
            CorpusConfig(**config_dict)
            return True, None
        except Exception as e:
            return False, str(e)

    def get_default_config(self) -> Dict[str, Any]:
        """Get default configuration template."""
        return {
            "metadata": {
                "name": "my_corpus",
                "display_name": "My Corpus",
                "description": "Description of my corpus",
                "version": "1.0.0",
                "time_period": {
                    "start": 1900,
                    "end": 2000
                },
                "entities": []
            },
            "source": {
                "type": "local",
                "location": "backend/corpus/sources"
            },
            "filters": {
                "method": "directory",
                "directory_depth": 1,
                "filters": []
            },
            "citation": {
                "template": "{author}. {title}. {date}. {source}.",
                "source_name": "My Corpus"
            },
            "embedding": {
                "model_id": "sentence-transformers/all-MiniLM-L6-v2",
                "chunk_size": 500,
                "chunk_overlap": 50,
                "batch_size": 32
            },
            "processing": {
                "mode": "cpu",
                "max_workers": 4
            }
        }

    def list_backups(self) -> List[Path]:
        """List available configuration backups."""
        if not self.backup_dir.exists():
            return []

        backups = list(self.backup_dir.glob("corpus_config_*.yaml"))
        return sorted(backups, reverse=True)  # Most recent first

    def restore_backup(self, backup_file: Path) -> bool:
        """Restore configuration from backup."""
        try:
            with open(backup_file, 'r') as f:
                data = yaml.safe_load(f)

            config = CorpusConfig(**data)
            return self.save_config(config)
        except Exception as e:
            print(f"Error restoring backup: {e}")
            return False