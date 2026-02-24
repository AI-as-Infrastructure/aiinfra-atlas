> **Note**: This file provides project context, OpenSpec workflow, and setup information for Claude Code to help understand the ATLAS codebase, conventions, and common operations. This is the single source of truth for AI assistants working on this project.

# ATLAS - AI Infrastructure Research Platform

## OpenSpec Workflow

This project uses [OpenSpec](https://github.com/Fission-AI/OpenSpec) for spec-driven development. When planning significant changes:

### When to Create an OpenSpec Change Proposal

Create a proposal when you need to:
- Add features or functionality
- Make breaking changes (API, schema)
- Change architecture or patterns
- Optimize performance (changes behavior)
- Update security patterns

Skip proposals for:
- Bug fixes (restore intended behavior)
- Typos, formatting, comments
- Dependency updates (non-breaking)
- Configuration changes
- Tests for existing behavior

### Quick Workflow

1. **Search existing work**: `openspec list` and `openspec list --specs`
2. **Create proposal**: Choose unique `change-id` (kebab-case, verb-led: `add-`, `update-`, `remove-`)
3. **Scaffold**: Create `proposal.md`, `tasks.md`, and spec deltas under `openspec/changes/<id>/`
4. **Validate**: `openspec validate <change-id> --strict`
5. **Implement**: Follow tasks sequentially
6. **Archive**: After deployment, use `openspec archive <change-id>`

**Full OpenSpec Documentation**: See `openspec/AGENTS.md` for complete workflow details, validation rules, and examples.

---

ATLAS: Analysis and Testing of Language Models for Archival Systems is a test harness for the evaluation of Large Language Model (LLM) Retrieval Augmented Generation (RAG) for Humanities & Social Science (HASS) research. ATLAS is a deliverable of the [AI as Infrastructure (AIINFRA)](https://aiinfra.anu.edu.au) project, focused on developing evaluation frameworks for LLM RAG systems designed for historical research.

**Research Tool Philosophy**: This is a research prototype emphasizing lean, well-documented code that fails fast. It follows amateur Research Software Engineering (RSE) practices - not intended as an enterprise application. The project makes heavy use of AI coding support.

## Development

### Prerequisites
- Python 3.10
- Node.js 22.14.0
- Redis server

### Setup
```bash
# Clone repository
git clone https://github.com/AI-as-Infrastructure/aiinfra-atlas.git
cd aiinfra-atlas

# Copy environment template
cp config/.env.template config/.env.development

# Start servers
make b  # Backend (auto-detects GPU)
make f  # Frontend
```

### First Run: Corpus Wizard

The repository ships clean with no pre-built corpus. After starting the servers:

1. Open http://localhost:5173 - lands on the **System Mode** page
2. In **Configure Mode**, open the **Corpus Wizard**
3. Follow the wizard: source selection, filters, embedding model, LLM target
4. Build the corpus (GPU-accelerated when available)
5. Enter **Deploy Mode** to lock configuration and start querying

The wizard generates all artifacts in `backend/corpus/`:
- `manifest.json` - Corpus metadata and statistics (v1.4 schema)
- `corpus_active.json` - Central runtime configuration (replaces env vars for corpus settings)
- `corpus_config.yaml` - Build configuration
- `chroma_db/` - Vector store
- `bm25_corpus.jsonl` - BM25 lexical index
- Retriever adapter `.py` file

### Configure / Deploy Mode Lifecycle

- **Configure Mode** (default on startup): Wizard and settings available. `.env` files updated.
- **Deploy Mode** (one-way lock): Configuration locked. Chat interface active. Server restart required to reconfigure.
- **ModeSelector.vue** is the application entry point / landing page.

Note: Frontend dependencies are installed automatically - see Makefile for development server commands.

## Production & Deployment

**Environment Management, Data & Utilities**: See Makefile for all deployment, backup, and utility commands.

**Getting Help**: Use `make help` to see all available commands, or `make help-<command>` for detailed help on specific commands.

## Architecture

### Key Directories
- `backend/` - FastAPI application with modular RAG pipeline
- `backend/corpus/` - Active corpus build artifacts (wizard-generated, gitignored)
- `backend/targets/` - Test target configuration `.txt` files
- `backend/modules/` - Core backend modules (config, LLM, retrieval, etc.)
- `backend/retrievers/` - Base retriever class and legacy retrievers
- `backend/routers/` - FastAPI route handlers including corpus_wizard.py and mode.py
- `frontend/` - Vue.js frontend for user interface
- `config/` - Environment configurations and requirements
- `docs/` - Documentation
- `deploy/` - Deployment scripts for dev/staging/production
- `create/` - Advanced/manual scripts for vector store and retriever creation

### Core Backend Modules
- `config.py` - Configuration from corpus_active.json, target files, and .env files
- `manifest_loader.py` - Loads manifest from backend/corpus/ (primary) or backend/targets/ (fallback)
- `mode_manager.py` - Configure/deploy mode state management
- `corpus_wizard.py` (router) - Wizard API endpoints for corpus building
- `corpus_builder.py` - Corpus build orchestration
- `corpus_analyzer.py` - Corpus structure analysis and filter discovery
- `llm.py` - Multi-provider LLM integration with telemetry
- `system_prompts.py` - Modular prompt construction
- `document_retrieval.py` - Vector store retrieval with corpus filtering
- `embeddings.py` - Embedding model management

### Technology Stack
- **Backend**: FastAPI, LangChain, ChromaDB, Redis, OpenTelemetry
- **Frontend**: Vue 3, Vite dev server
- **LLM Providers**: OpenAI, Anthropic, Google, AWS Bedrock, Ollama
- **Vector Store**: ChromaDB with Sentence Transformers (BERT-based embeddings)
- **Monitoring**: Phoenix (optional), comprehensive telemetry
- **Deployment**: Python venv, NVM for Node.js version management
- **Requirements**: Managed via pyproject.toml with optional dependencies (regenerate lock with `make l` if needed)

## Configuration

### Configuration Sources (precedence order)
1. `corpus_active.json` - Corpus settings (created by deploy mode from manifest data)
2. Test target files (`backend/targets/{target}.txt`) - LLM and search parameters
3. `.env.{environment}` files - API keys, Redis, telemetry, authentication
4. `config/system_settings.json` - Runtime toggles (telemetry, inter-rater)

### Environment Files
- `config/.env.development` - Development settings
- `config/.env.staging` - Staging environment settings
- `config/.env.production` - Production settings (server-only)

### Test Targets
ATLAS uses "test targets" to configure LLM models and parameters:
- Located in `backend/targets/{target}.txt`
- Defines LLM provider, model, and retrieval settings
- Generated by the wizard or created manually

### Phoenix Telemetry Configuration
ATLAS uses Phoenix Arize for LLM observability and telemetry. The default configuration is generic for open source use:
- **PHOENIX_SPACE_ID**: Set to `atlas` by default - customize for your Phoenix space
- **PHOENIX_PROJECT_NAME**: Uses generic `ATLAS-Dev`, `ATLAS-Staging`, `ATLAS-Prod` naming
- **Configuration**: All environment files use Bearer token authentication for Phoenix Cloud spaces
- Users should create their own Phoenix space and update environment variables accordingly

## Documentation

See `docs/` directory for detailed guides:
- `development.md` - Complete development setup guide
- `key_modules.md` - Backend architecture overview
- `configuration.md` - Configuration options (wizard-managed vs .env)
- `corpus_wizard.md` - Corpus wizard interface and filter discovery
- `production.md` - Production deployment guide
- `staging.md` - Staging environment setup
- `test_targets.md` - Test target configuration
- `telemetry.md` - Monitoring and telemetry
- `RAG_search.md` - RAG pipeline details
- `manifest.md` - Manifest schema (v1.4)

## Development Philosophy & Ethics

### Research Software Engineering (RSE)
- **Lean codebase**: Minimal, well-documented code without unnecessary fallbacks
- **Fail fast**: Code designed to fail quickly and clearly rather than degrade gracefully
- **Prototype focus**: Research tool, not enterprise application
- **Amateur RSE practices**: Emphasis on clarity and research utility over enterprise patterns

### Data Ethics & Privacy
- **FAIR protocols**: Findable, Accessible, Interoperable, Reusable data practices
- **CARE protocols**: Collective benefit, Authority to control, Responsibility, Ethics for indigenous data
- **User privacy paramount**: Users must not be identifiable in any data or logs
- **Research ethics**: Designed for academic and research use with ethical data handling

## Common Failure Points & Debugging

### User Feedback
**Issue**: User feedback not being recorded or associated correctly
**Root Cause**: Feedback association with telemetry spans breaks between environments
- **Development**: Uses SQLite for span storage
- **Production**: Uses Redis for span storage
**Critical Config**: `REDIS_URL` must be present in .env files - feedback will fail without it
**Debug**: Check span ID matching between feedback submission and telemetry storage

### Environment Configuration Failures
- **Missing REDIS_URL**: Feedback system fails completely without Redis connection string
- **Wrong .env file**: Ensure correct environment file is loaded (development/staging/production)
- **API keys missing**: LLM providers fail without valid keys - no graceful degradation
- **No corpus built**: Application requires corpus wizard to be run before querying

### Corpus / Filter Failures
- **Missing manifest**: `manifest_loader.py` checks `backend/corpus/manifest.json` first, then falls back to `backend/targets/manifest.json`
- **Filters not showing**: Verify `manifest.json` has `fields.corpus.values` with more than one entry
- **corpus_active.json missing**: Created by deploy mode; ensure you entered deploy mode after building
- **Retriever not found**: `load_retriever()` checks `backend/corpus/` first, then `backend/retrievers/`

### Other Common Failures
- **Port conflicts**: Dev servers fail on occupied ports (8000, 5173) - no automatic port switching
- **Redis connection loss**: Production feedback fails if Redis unavailable - no fallback by design

### Debugging Strategy (Fail-Fast Approach)
1. **Check environment first**: Verify .env file has all required variables including `REDIS_URL`
2. **Check corpus**: Verify `backend/corpus/manifest.json` and `corpus_active.json` exist
3. **Read logs immediately**: No silent failures - errors should be explicit
4. **Test components individually**: LLM, vector store, Redis connections
5. **Use telemetry traces**: Follow request flow to identify exact failure point

## Notes

- The tool is designed to be corpus-agnostic. The code and documentation should not assume any specific corpus content.
- The repository ships clean; users build their own corpus via the wizard
- Telemetry with Phoenix monitoring (anonymized)
- Multi-provider LLM support with prompt caching
- Real-time streaming responses via Server-Sent Events
- Production deployment designed for server-side execution
- Avoid fallback mechanisms - designed to fail clearly when issues occur
- Terse comments - 'documentation' not 'comprehensive documentation'
