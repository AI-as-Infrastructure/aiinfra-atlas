# Corpus Configuration Wizard

The ATLAS Corpus Configuration Wizard provides a user-friendly interface for configuring and swapping between different text corpora used for RAG (Retrieval Augmented Generation).

## Overview

The corpus wizard allows:
- Configuration of new corpora from local directories or GitHub repositories
- Dynamic filter generation based on corpus structure
- Embedding model selection with period-specific defaults
- Real-time build progress tracking
- Atomic corpus swapping with automatic backup
- **Isolated environment** that doesn't interfere with main development

## Key Design Principles

### 1. Isolated Environment
- **Corpus operations use `.venv_corpus`** - separate from main dev environment
- **Main app uses `.venv`** - for running the backend/frontend servers
- **Clean separation** - corpus building won't affect your dev dependencies

### 2. Explicit Setup
- **Choose CPU or GPU version** - User decides based on their hardware
- **`make corpus-wizard-cpu`** - Smaller download (~200MB), no GPU needed
- **`make corpus-wizard-gpu`** - Larger download (~2GB), for NVIDIA GPUs

### 3. Clean Removal
- **`make corpus-clean`** - Removes corpus environment cleanly
- **Preserves data** - Keeps your configurations, backups, and active corpus
- **Ready for `make b/p`** - After cleanup, dev/prod environments work normally

## Quick Start

### Initial Setup

Choose the setup based on your hardware:

```bash
# For systems WITHOUT NVIDIA GPU (smaller ~200MB download)
make corpus-wizard-cpu

# For systems WITH NVIDIA GPU (larger ~2GB download, faster processing)
make corpus-wizard-gpu

# Start servers if not running
make b  # Terminal 1: Backend
make f  # Terminal 2: Frontend

# Navigate to corpus wizard
# Open http://localhost:5173/corpus-wizard
```

#### Which version to choose?
- **`make corpus-wizard-cpu`** - Choose this if:
  - You don't have an NVIDIA GPU
  - You want smaller download size (~200MB)
  - You're fine with CPU-based processing

- **`make corpus-wizard-gpu`** - Choose this if:
  - You have an NVIDIA GPU with CUDA support
  - You want faster embedding generation
  - You don't mind larger download (~2GB)

### Quick Corpus Swapping
```bash
# Switch to pre-configured corpora
make use-hansard  # Hansard parliamentary corpus
make use-darwin   # Darwin correspondence corpus

# Or use any saved configuration
make corpus-swap CORPUS=my_custom_corpus
```

### Cleanup
```bash
# Remove corpus environment (preserves data)
make corpus-clean
```

### Production Deployment

The corpus wizard deploys with the main application:

```bash
# On production server
make p  # Deploy production (includes corpus wizard)
```

### Dependencies

The corpus wizard requires the following additional dependency:
- `gitpython==3.1.41` - For GitHub corpus integration

This is included in `config/requirements.txt` and will be installed automatically.

## Usage

### Web Interface

Navigate to `/corpus-wizard` in your browser to access the wizard interface.

### Command Line

#### Complete Command Reference

**Setup & Management:**
```bash
# CPU-only setup (smaller download ~200MB)
make corpus-wizard-cpu

# GPU/CUDA setup (larger download ~2GB, for NVIDIA GPUs)
make corpus-wizard-gpu

# Clean up corpus environment (preserves data)
make corpus-clean

# List available corpus configurations
make corpus-list
```

**Corpus Operations:**
```bash
# Build corpus from configuration
make corpus-build CONFIG=corpus_configs/my_corpus.yaml

# Backup current corpus
make corpus-backup

# Restore from most recent backup
make corpus-restore

# Swap to different corpus
make corpus-swap CORPUS=my_custom_corpus
```

**Quick Swap Commands:**
```bash
# Pre-configured corpus shortcuts
make use-hansard  # Hansard parliamentary corpus
make use-darwin   # Darwin correspondence corpus
```

#### Environment Structure

```
aiinfra-atlas/
├── .venv/              # Main development environment (for make b/f/p)
├── .venv_corpus/       # Isolated corpus environment (for corpus operations)
├── corpus_configs/     # Saved corpus configurations
├── corpus_backups/     # Automatic backups
└── backend/targets/    # Active corpus vector store
```

## Architecture

### Backend Components

- `backend/modules/corpus_config.py` - Configuration models and validation
- `backend/modules/corpus_analyzer.py` - Corpus structure analysis
- `backend/modules/github_corpus.py` - GitHub repository integration
- `backend/modules/corpus_requirements.py` - System requirements checking
- `backend/routers/corpus_wizard.py` - API endpoints
- `create/create_corpus_store.py` - Universal corpus builder

### Frontend Components

- `frontend/src/pages/CorpusWizardComplete.vue` - Main wizard interface
- `frontend/src/components/wizard/` - Wizard step components

### Configuration Storage

Corpus configurations are stored as YAML files in:
- `corpus_configs/` - Saved corpus configurations
- `corpus_backups/` - Automatic backups of previous corpora

## Corpus Configuration Format

```yaml
metadata:
  name: "Corpus Name"
  description: "Description of the corpus"
  time_period_from: 1800
  time_period_to: 1900
  copyright_status: "public_domain|mixed|restricted"
  copyright_statement: "Copyright information"
  doi: "10.5281/zenodo.example"
  citation: "How to cite this corpus"

source:
  type: "local|github"
  location: "/path/to/files or https://github.com/org/repo"
  branch: "main"  # For GitHub sources
  path: "subfolder/"  # Optional subfolder
  file_types: ["txt", "xml"]

filters:
  - id: "filter_id"
    label: "Display Label"
    pattern: "**/*.txt"  # Glob pattern

embeddings:
  model: "Livingwithmachines/bert_1760_1900"
  pooling: "mean|mean+max"
  chunk_size: 1000
  chunk_overlap: 100

vector_store:
  type: "chromadb"
  collection_name: "corpus_name"

search:
  type: "hybrid"
  k_default: 10
```

## System Requirements

The corpus wizard automatically checks system requirements before building:
- Python 3.10+
- Sufficient disk space (varies by corpus size)
- CPU or GPU support for embeddings
- Git (for GitHub sources)
- Internet connection (for downloading models/repos)

## Progress Tracking

The build process provides real-time progress via Server-Sent Events:
- Document processing progress
- Filter generation progress
- Embedding generation progress
- Vector store creation progress
- Detailed logging of all operations

## Security Considerations

- GitHub tokens are handled securely (never stored in configs)
- Corpus configurations are validated before building
- Automatic backups prevent data loss
- Atomic swapping ensures consistency

## Troubleshooting

### Common Issues

1. **Build fails with memory error**
   - Use smaller batch sizes in embeddings config
   - Switch to CPU mode if GPU memory is limited

2. **GitHub repository not accessible**
   - Check repository is public or provide access token
   - Verify branch and path exist

3. **Corpus swap fails**
   - Check disk space for backup
   - Ensure no processes are using the corpus

## Best Practices

1. **Test configurations locally first** before deploying to production
2. **Use descriptive filter IDs** for better user experience
3. **Include complete metadata** for research reproducibility
4. **Regular backups** are created automatically but can be triggered manually
5. **Monitor disk usage** as corpora and backups can be large

## Future Enhancements

- Support for additional source types (S3, Azure, etc.)
- Incremental corpus updates
- Multi-corpus search capabilities
- Corpus versioning and rollback
- Automated corpus quality assessment