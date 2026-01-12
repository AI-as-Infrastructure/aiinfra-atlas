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
- Git LFS

### Setup
```bash
# Clone and setup Git LFS
git lfs install
git lfs pull              # Pull default vector store

# Copy environment template
cp config/.env.template config/.env.development
```

**Backend, vector store, and development server setup**: See Makefile for all available commands.

**Vector Store Options:**
- **Default**: Pre-generated vector store included (uses mean pooling fallback if fine-tuned models unavailable)
- **Custom**: See Makefile for vector store creation commands

Note: Frontend dependencies are installed automatically - see Makefile for development server commands.

## Production & Deployment

**Environment Management, Data & Utilities**: See Makefile for all deployment, backup, and utility commands.

**Getting Help**: Use `make help` to see all available commands, or `make help-<command>` for detailed help on specific commands.

## Architecture

### Key Directories
- `backend/` - FastAPI application with modular RAG pipeline
- `frontend/` - Vue.js frontend for user interface
- `config/` - Environment configurations and requirements
- `docs/` - Documentation
- `deploy/` - Deployment scripts for dev/staging/production
- `create/` - Scripts to create a new vector store and associated retriever
- `backend/targets/` - Test target configurations for different LLM setups
- `backend/modules/` - Core backend modules (config, LLM, retrieval, etc.)

### Core Backend Modules
- `config.py` - Centralized configuration management
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
- **Requirements**: System-specific requirements.lock (regenerate with `make l` if needed)

## Configuration

### Environment Files
- `config/.env.development` - Development settings
- `config/.env.staging` - Staging environment settings
- `config/.env.production` - Production settings (server-only)

### Test Targets
ATLAS uses "test targets" to configure LLM models and parameters:
- Located in `backend/targets/{target}.txt`
- Defines LLM provider, model, and retrieval settings
- Current target set via `TEST_TARGET` environment variable

## Documentation

See `docs/` directory for detailed guides:
- `development.md` - Complete development setup guide
- `key_modules.md` - Backend architecture overview
- `configuration.md` - Configuration options
- `production.md` - Production deployment guide
- `staging.md` - Staging environment setup
- `test_targets.md` - Test target configuration
- `telemetry.md` - Monitoring and telemetry
- `RAG_search.md` - RAG pipeline details

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
- **Environment variable mismatch**: Check all required variables are set for current environment

### Other Common Failures
- **Vector store corruption**: ChromaDB files inconsistent - see Makefile for rebuild commands
- **Model loading issues**: Embedding models fail to load - check model directory and permissions
- **Port conflicts**: Dev servers fail on occupied ports (8000, 5173) - no automatic port switching
- **Redis connection loss**: Production feedback fails if Redis unavailable - no fallback by design

### Debugging Strategy (Fail-Fast Approach)
1. **Check environment first**: Verify .env file has all required variables including `REDIS_URL`
2. **Read logs immediately**: No silent failures - errors should be explicit
3. **Test components individually**: LLM, vector store, Redis connections
4. **Use telemetry traces**: Follow request flow to identify exact failure point

## Notes

- The default project focuses on 1901 parliamentary records from Australia, NZ, UK but the tool is designed to allow the corpus to be changed. The code and documentation should be agnostic of the vector store content.
- Uses LFS for large model files and vector databases
- Telemetry with Phoenix monitoring (anonymized)
- Multi-provider LLM support with prompt caching
- Real-time streaming responses via Server-Sent Events
- Production deployment designed for server-side execution
- Avoid fallback mechanisms - designed to fail clearly when issues occur
- Terse comments - 'documentation' not 'comprehensive documentation'
