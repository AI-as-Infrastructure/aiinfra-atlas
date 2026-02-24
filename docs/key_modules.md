# Key Backend Modules

Overview of the core backend modules and their responsibilities.

## Architecture

```
backend/
├── corpus/                  # Active corpus (wizard-generated, gitignored)
│   ├── manifest.json        # Corpus metadata and stats (v1.4)
│   ├── corpus_active.json   # Runtime configuration
│   ├── corpus_config.yaml   # Build configuration
│   ├── chroma_db/           # Vector store
│   ├── bm25_corpus.jsonl    # BM25 lexical index
│   └── {name}_adapter.py    # Retriever adapter
├── modules/                 # Core application modules
│   ├── config.py            # Configuration management
│   ├── manifest_loader.py   # Manifest loading and corpus options
│   ├── mode_manager.py      # Configure/deploy mode state
│   ├── corpus_config.py     # Corpus configuration models
│   ├── corpus_analyzer.py   # Corpus structure analysis
│   ├── corpus_builder.py    # Corpus build orchestration (internal)
│   ├── github_corpus.py     # GitHub repository integration
│   ├── corpus_requirements.py  # System requirements checking
│   ├── llm.py               # Multi-provider LLM integration
│   ├── system_prompts.py    # Prompt construction
│   ├── document_retrieval.py # Vector store retrieval
│   ├── embeddings.py        # Embedding model management
│   ├── feedback.py          # User feedback handling
│   └── telemetry.py         # OpenTelemetry instrumentation
├── retrievers/              # Retriever framework
│   ├── base_retriever.py    # Base class for all retrievers
│   └── __init__.py          # Dynamic retriever loading
├── routers/                 # FastAPI route handlers
│   ├── corpus_wizard.py     # Wizard API endpoints
│   ├── mode.py              # Mode management endpoints
│   ├── system_configuration.py  # System settings API
│   └── ...                  # Other route handlers
└── targets/                 # Test target .txt files
```

## Configuration Layer

### config.py

Central configuration module. Loads settings from:
1. `corpus_active.json` (corpus settings - retriever module, collection, embedding model)
2. Test target files (LLM provider, model, search parameters)
3. `.env.{environment}` files (API keys, Redis, telemetry)

Does not use environment variables for corpus settings.

### manifest_loader.py

Loads and parses `manifest.json`. Checks `backend/corpus/manifest.json` first (wizard output), falls back to `backend/targets/manifest.json` for backward compatibility.

Key functions:
- `load_manifest()` - Load the full manifest dictionary
- `get_corpus_options()` - Extract filter values for the frontend dropdown
- `generate_corpus_label()` - Create display labels from corpus IDs

### mode_manager.py

Manages the configure/deploy mode lifecycle:
- **Configure Mode**: Wizard and settings accessible, configuration can change
- **Deploy Mode**: One-way lock, chat interface active, `corpus_active.json` created from manifest
- Server restart required to return to configure mode

## Corpus Wizard Layer

### corpus_wizard.py (router)

FastAPI router for the wizard UI. Endpoints include:
- `POST /api/corpus/analyze` - Analyze a source directory
- `POST /api/corpus/build` - Start a corpus build (SSE progress stream)
- `POST /api/corpus/activate` - Activate a built corpus
- `GET /api/corpus/status` - Get current corpus status

### corpus_analyzer.py

Analyzes source directories to discover file structure and suggest filters. Uses a hybrid approach:
1. Directory structure (highest priority) - folder names become filters
2. User metadata hints (medium) - time periods, people, topics
3. Content analysis (lowest) - XML/text metadata sampling

### corpus_builder.py

Orchestrates the full build pipeline internally (called by the wizard router):
- Document chunking and processing
- Embedding generation (GPU or CPU)
- ChromaDB vector store creation
- BM25 index generation
- Manifest writing
- Retriever adapter generation

### corpus_config.py

Pydantic models for corpus configuration validation: metadata, source, filters, embeddings, vector store, and search parameters.

## Retrieval Layer

### document_retrieval.py

Handles document retrieval from the vector store with corpus filtering. Supports:
- Dense retrieval (ChromaDB similarity search)
- Hybrid retrieval (dense + BM25 via Reciprocal Rank Fusion)
- Corpus filter application

### retrievers/__init__.py

Dynamic retriever loading. `load_retriever()` searches:
1. `backend/corpus/{name}` (wizard-generated adapters)
2. `backend/retrievers/{name}` (legacy/manual retrievers)

Finds and instantiates the `BaseRetriever` subclass from the module.

### retrievers/base_retriever.py

Abstract base class for all retrievers. Defines:
- `retrieve(query, k, filter)` - Main retrieval method
- `get_filter_capabilities()` - Available corpus filters
- `get_corpus_options()` - Frontend dropdown options

### embeddings.py

Manages embedding model loading with GPU auto-detection and CPU fallback. Handles Sentence Transformers with configurable pooling.

## LLM Layer

### llm.py

Multi-provider LLM integration with OpenTelemetry instrumentation. Supports:
- OpenAI, Anthropic, Google, AWS Bedrock, Ollama
- Streaming responses via Server-Sent Events
- Prompt caching (Anthropic)
- Concurrent request management

### system_prompts.py

Constructs system prompts from modular components. Prompt content adapts based on the active corpus and configuration.

## Supporting Modules

### feedback.py

User feedback collection and storage. Routes feedback to Redis (production) or SQLite (development) and associates it with telemetry spans.

### telemetry.py

OpenTelemetry instrumentation for request tracing. Exports to Phoenix for observability. Spans capture: query, retrieval, LLM call, response, and feedback.

### mode.py (router)

Mode management API:
- `GET /api/mode` - Current mode and corpus info
- `POST /api/mode/deploy` - Enter deploy mode (creates `corpus_active.json`)
- Extracts corpus info from manifest for display

### system_configuration.py (router)

Runtime settings API:
- `GET /api/system/configuration` - Current system settings
- `POST /api/system/configuration` - Update toggles (telemetry, inter-rater)
- Persists to `config/system_settings.json`

## Data Flow

```
User Query
  -> Frontend (UserInput.vue)
    -> Backend API (FastAPI router)
      -> config.py (load corpus_active.json + target)
      -> document_retrieval.py (retrieve relevant chunks)
        -> Retriever adapter (backend/corpus/{name}_adapter.py)
          -> ChromaDB (dense search)
          -> BM25 index (lexical search, if hybrid)
          -> RRF fusion
      -> llm.py (generate response with retrieved context)
        -> LLM Provider API
      -> telemetry.py (trace the request)
    -> SSE stream response
  -> Frontend (ChatHistory.vue)
```

## Related Documentation

- [Configuration Guide](configuration.md) - Configuration architecture and precedence
- [RAG Search](RAG_search.md) - Retrieval pipeline details
- [Corpus Wizard](corpus_wizard.md) - Wizard interface and filter discovery
- [Manifest Schema](manifest.md) - Manifest v1.4 format
- [Test Targets](test_targets.md) - LLM configuration
