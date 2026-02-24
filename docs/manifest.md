# Vector Store Manifest

The manifest (`manifest.json`) is a machine-readable record of how a vector store was built. It is generated automatically during corpus creation (by the wizard or manual scripts) and stored at `backend/corpus/manifest.json`.

## Schema Version

Current schema version: **1.4**

The manifest is corpus-agnostic and does not assume any specific corpus content.

## Location

- **Primary**: `backend/corpus/manifest.json` (wizard-generated)
- **Fallback**: `backend/targets/manifest.json` (legacy/backward compatibility)

The `manifest_loader.py` module checks the primary location first.

## Schema

### Top-Level Structure

```json
{
  "schema_version": "1.4",
  "created_at": "2025-07-01T10:00:00Z",
  "corpus_name": "my_corpus",
  "display_name": "My Research Corpus",
  "description": "Description of the corpus",

  "embedding_model": {
    "id": "Livingwithmachines/bert_1890_1900",
    "type": "sentence-transformers",
    "pooling": "mean",
    "vector_size": 768
  },

  "vector_store": {
    "type": "chromadb",
    "collection_name": "my_corpus",
    "persist_directory": "backend/corpus/chroma_db"
  },

  "chunk_size": 1000,
  "chunk_overlap": 100,

  "fields": {
    "corpus": {
      "values": ["all", "1901_au", "1901_nz", "1901_uk"],
      "labels": {
        "all": "All Documents",
        "1901_au": "Australia",
        "1901_nz": "New Zealand",
        "1901_uk": "United Kingdom"
      }
    }
  },

  "statistics": {
    "total_documents": 206,
    "total_chunks": 4521,
    "by_corpus": {
      "1901_au": { "documents": 70, "chunks": 1520 },
      "1901_nz": { "documents": 68, "chunks": 1480 },
      "1901_uk": { "documents": 68, "chunks": 1521 }
    }
  },

  "build": {
    "environment": "gpu",
    "duration_seconds": 45.2,
    "build_tool": "corpus_wizard",
    "python_version": "3.10.12"
  },

  "search": {
    "type": "hybrid",
    "bm25_corpus": "backend/corpus/bm25_corpus.jsonl"
  },

  "metadata": {
    "time_period_from": 1901,
    "time_period_to": 1901,
    "material_type": "parliamentary",
    "copyright_status": "public_domain"
  },

  "citation": {
    "text": "Corpus built with ATLAS Corpus Wizard",
    "doi": "",
    "url": ""
  },

  "inter_rater": {
    "enabled": false,
    "config": {}
  }
}
```

### Key Sections

#### embedding_model (nested in v1.2+)

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Hugging Face model identifier |
| `type` | string | Model framework (e.g., `sentence-transformers`) |
| `pooling` | string | Pooling strategy: `mean`, `cls`, or `mean+max` |
| `vector_size` | integer | Embedding dimension |

#### vector_store (nested in v1.2+)

| Field | Type | Description |
|-------|------|-------------|
| `type` | string | Vector store type (currently `chromadb`) |
| `collection_name` | string | ChromaDB collection name |
| `persist_directory` | string | Path to persisted store |

#### fields.corpus

| Field | Type | Description |
|-------|------|-------------|
| `values` | array | List of corpus filter IDs (includes `all`) |
| `labels` | object | Mapping of filter ID to display label |

These values populate the corpus filter dropdown in the frontend. The frontend shows filters only when `values` has more than one entry.

#### statistics

Build statistics including total documents, total chunks, and per-corpus breakdowns.

#### build (v1.4)

| Field | Type | Description |
|-------|------|-------------|
| `environment` | string | `gpu` or `cpu` |
| `duration_seconds` | float | Build time |
| `build_tool` | string | `corpus_wizard` or `manual` |
| `python_version` | string | Python version used |

#### search

| Field | Type | Description |
|-------|------|-------------|
| `type` | string | `hybrid` or `dense` |
| `bm25_corpus` | string | Path to BM25 JSONL file (if hybrid) |

## Generation

The manifest is generated automatically by:
- **Wizard**: During the corpus build process, written to `backend/corpus/manifest.json`
- **Manual scripts**: During `make vs`, written to `create/output/manifest.json`

## Runtime Usage

### manifest_loader.py

The backend loads the manifest on startup via `manifest_loader.py`:

```python
from backend.modules.manifest_loader import load_manifest, get_corpus_options

manifest = load_manifest()  # Returns dict or {}
options = get_corpus_options()  # Returns list of {value, label} dicts
```

### Frontend Filters

`get_corpus_options()` extracts `fields.corpus.values` and generates labels. The result populates the corpus filter dropdown. Filters are hidden when only one option exists.

### Mode Display

`mode.py` reads the manifest to display corpus information on the System Mode page (embedding model, collection name, document count).

## Schema Evolution

| Version | Changes |
|---------|---------|
| 1.0 | Initial flat schema |
| 1.2 | Nested `embedding_model` and `vector_store` objects |
| 1.3 | Added `fields.corpus.labels`, `statistics.by_corpus` |
| 1.4 | Added `build` section, `search` section, `inter_rater` config |

The backend handles both flat (v1.0) and nested (v1.2+) formats for backward compatibility.

## Related Documentation

- [Configuration Guide](configuration.md) - How manifest feeds into runtime configuration
- [Corpus Wizard](corpus_wizard.md) - How the wizard generates the manifest
- [Vector Store Creation](create_store.md) - Build pipeline details
- [Key Modules](key_modules.md) - manifest_loader.py module details
