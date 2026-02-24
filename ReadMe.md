# ATLAS Project

## Overview
ATLAS: Analysis and Testing of Language Models for Archival Systems is a test harness for the evaluation of Large Language Model (LLM) Retrieval Augmented Generation (RAG) for Humanities & Social Science (HASS) research. ATLAS is a deliverable of the [AI as Infrastructure (AIINFRA)](https://aiinfra.anu.edu.au) project. AIINFRA's primary goal is to develop an evaluation framework for LLM RAG systems designed for historical research.

## Major Releases
v0.2.0: https://github.com/AI-as-Infrastructure/aiinfra-atlas/releases/tag/v0.2.0 | https://doi.org/10.5281/zenodo.17204370.

## Project Status
The project is under active development and makes heavy use of AI coding support. The tool supports authenticated access (AWS Cognito), implements hybrid search (BM25 + dense via RRF), and has been exercised in load-testing scenarios up to ~30 concurrent users. The corpus is user-configurable via the built-in wizard.

## Environment Requirements

- **Python:** 3.10 (required for backend and all scripts)
- **Node.js:** 22.14.0 (required for frontend; enforced via .nvmrc and package.json)
- **Redis:** Required for caching and feedback
- **uv:** Modern Python package installer (optional but recommended for 10-100x faster dependency installation)
  - Install: `curl -LsSf https://astral.sh/uv/install.sh | sh`
  - Falls back to pip if not available
- **Dependency Management:** Uses `pyproject.toml` with optional dependencies for PyTorch GPU/CPU variants
- GPU support is auto-configured at startup based on detected hardware

## Core Components
ATLAS is built using the following technologies:

- FastAPI
- Vue 3
- Vite
- Chroma DB
- LangChain
- OpenTelemetry
- Phoenix Arize (optional)

Other dependencies include: Python virtual environments (`venv`), NVM, Sentence Transformers for embeddings, `rank-bm25` for BM25 lexical search (hybrid mode), and optional LLM providers (OpenAI, Anthropic, Ollama, etc.).

## Quick Start

1. Clone the repository:
   ```bash
   git clone https://github.com/AI-as-Infrastructure/aiinfra-atlas.git
   cd aiinfra-atlas
   ```
2. Copy and configure environment:
   ```bash
   cp config/.env.template config/.env.development
   # Edit config/.env.development with your API keys
   ```
3. Start the servers:
   ```bash
   # Terminal 1 - Backend (FastAPI + ChromaDB)
   make b

   # Terminal 2 - Frontend (Vue + Vite)
   make f
   ```
4. Open http://localhost:5173 in your browser. You will land on the **System Mode** page.
5. Navigate to the **Corpus Wizard** to build your first corpus:
   - Select source directory or GitHub repository
   - Configure embedding model and filters
   - Configure LLM test target
   - Build and deploy
6. Enter **Deploy Mode** to lock configuration and begin querying.

## Command Reference

ATLAS uses a simplified command structure for common operations. Here are the main commands:

### Development
- `make b` - Start backend development server (auto-detects GPU)
- `make f` - Start frontend development server
- `make d` - Destroy development environment

### Deployment
- `make p` - Deploy to production
- `make dp` - Delete production environment
- `make sl` - Deploy to local staging environment
- `make sr` - Deploy to remote staging environment
- `make dsl` - Delete local staging environment
- `make dsr` - Delete remote staging environment

### Utilities
- `make l` - Generate requirements.lock from pyproject.toml
- `make c` - Check Python environment

### Corpus Management
- `make corpus-list` - List available corpus configurations
- `make corpus-backup` - Backup current corpus
- `make corpus-restore` - Restore from most recent backup

### Analysis and Monitoring
- `make backup-prod` - Backup Phoenix telemetry data from production
- `make hansard-analysis` - Run analysis with visualizations

For detailed help on any command, use:
```bash
make help-<command>
# Example: make help-b
```

To see all available commands:
```bash
make help
```

## Corpus Setup

ATLAS uses a wizard-driven workflow for corpus configuration. The repository ships clean with no pre-built corpus; you build your own via the wizard.

### Wizard Workflow (Primary)

1. Start the backend and frontend (`make b`, `make f`)
2. Open http://localhost:5173 - you will land on the System Mode page
3. In Configure Mode, open the Corpus Wizard
4. Follow the wizard steps: source selection, filter configuration, embedding model, LLM target
5. Build the corpus (GPU-accelerated when available)
6. Enter Deploy Mode to lock configuration and start querying

The wizard generates all required artifacts in `backend/corpus/`:
- `manifest.json` - Corpus metadata and statistics
- `corpus_active.json` - Runtime configuration
- `corpus_config.yaml` - Build configuration
- `chroma_db/` - Vector store
- `bm25_corpus.jsonl` - BM25 lexical index
- Retriever adapter `.py` file

### Advanced: Manual Vector Store Creation

For advanced users or scripted builds, see the `create/` directory for template scripts:
```bash
make vs      # Build vector store (uses GPU if available)
make r       # Generate retriever
```

## Additional Documentation

### Architecture and Configuration
- [Analysis](docs/analysis.md) - Phoenix backup data analysis for user feedback and system performance
- [Authentication](docs/authentication.md) - AWS Cognito setup and configuration
- [Backups](docs/backups.md) - Phoenix telemetry data backup configuration and automation
- [Configuration Guide](docs/configuration.md) - Environment files, API keys, and system configuration
- [Corpus Wizard](docs/corpus_wizard.md) - Wizard interface, filter discovery, and corpus configuration
- [Data Privacy](docs/data_privacy.md) - Anonymity, telemetry, and PII avoidance
- [GPU Compatibility](docs/gpu_compatibility.md) - Automatic GPU detection and configuration (supports all NVIDIA generations: GTX 10xx through RTX 50xx)
- [Test Targets](docs/test_targets.md) - LLM configurations, vector store integration, and target management
- [Key Modules](docs/key_modules.md) - Core backend modules and their responsibilities
- [Vector Store Manifest](docs/manifest.md) - Corpus-agnostic schema, generation, and usage

### Development and Deployment
- [Development Environment](docs/development.md) - Local development setup, workflow, and debugging
- [Testing](docs/testing.md) - Test suite, running tests, and writing new tests
- [Staging Environment](docs/staging.md) - Local staging deployment for development and testing
- [Production Deployment](docs/production.md) - Complete production deployment guide with SSL, systemd services, and maintenance
- [Health Monitoring](docs/health_monitoring.md) - System health checks, monitoring, and troubleshooting
- [Load Testing Framework](docs/load_testing.md) - Performance testing and optimization guidelines
- [Vector Store Creation](docs/create_store.md) - Building and managing vector stores (advanced)

### User Interface and Features
- [FAQ](frontend/src/pages/FAQPage.vue) - Frequently asked questions and system limitations
- [Inter-rater Ratings](docs/inter_rater.md) - End-to-end flow, configuration, privacy

## License
- [License](LICENSE.md)
