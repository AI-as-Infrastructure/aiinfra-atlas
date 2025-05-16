# ATLAS Project

## Overview
This is a test harness for the evaluation of Large Language Model (LLM) Retrieval Augmented Generation (RAG) for Humanities & Social Science (HASS) research. ATLAS is a deliverable of the [AI as Infrastructure (AIINFRA)](https://aiinfra.anu.edu.au) project. AIINFRA's primary goal is to develop an evaluation framework for LLM RAG systems designed for historical research.

## Quick Start

1. Clone the repository
2. Set up environment variables (see [Configuration Guide](docs/getting-started/configuration.md))
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   npm install
   ```
4. Start the development servers:
   ```bash
   # Terminal 1 - Backend
   python backend/app.py
   
   # Terminal 2 - Frontend
   npm run dev
   ```

## Documentation

### Getting Started
- [Installation Guide](docs/getting-started/installation.md)
- [Configuration Guide](docs/getting-started/configuration.md)
- [Quick Start Tutorial](docs/getting-started/quick-start.md)

### Architecture
- [System Overview](docs/architecture/overview.md)
- [Backend Architecture](docs/architecture/backend.md)
- [Frontend Architecture](docs/architecture/frontend.md)
- [Data Flow](docs/architecture/data-flow.md)
- [Retriever System](docs/architecture/retriever-system.md)

#### Unified Configuration System
ATLAS uses a unified configuration system managed by `TargetConfig`. All settings (environment variables and target `.txt` files) are loaded dynamically at startup and made available to the retriever, API, UI, and telemetry. The `/api/config` endpoint returns the complete, current configuration for use in the UI and export functionality. This ensures a single source of truth for all runtime configuration.

### Features
- [Corpus Filtering](docs/features/corpus-filtering.md)
- [Feedback System](docs/features/feedback-system.md)
- [Citation System](docs/features/citation-system.md)
- [Chat Interface](docs/features/chat-interface.md)

### Deployment
- [Local Deployment](docs/deployment/local.md)
- [Production Deployment](docs/deployment/production.md)
- [Docker Deployment](docs/deployment/docker.md)
- [Environment Variables](docs/deployment/environment-variables.md)

### Development
- [Development Setup](docs/development/setup.md)
- [Contributing Guidelines](docs/development/contributing.md)
- [Testing Procedures](docs/development/testing.md)
- [Code Style Guide](docs/development/code-style.md)

### API Reference
- [API Endpoints](docs/api/endpoints.md)
- [Streaming API](docs/api/streaming.md)
- [Telemetry API](docs/api/telemetry.md)

### Vector Store
- [Vector Store Overview](docs/vector-store/overview.md)
- [Redis Configuration](docs/vector-store/redis.md)
- [Embedding Models](docs/vector-store/embeddings.md)
- [Indexing Process](docs/vector-store/indexing.md)

### Vector Store & Retriever Generation Workflow

ATLAS supports an automated workflow for building new vector stores and generating compatible retrievers:

- The `create/` directory contains template scripts for generating vector stores (e.g., Hansard) and matching retriever classes.
- You can add new corpora (e.g., novels, newspapers) by copying and adapting these scripts.
- The following Makefile targets are available:

```bash
make store      # Builds the vector store using create/create_hansard_store.py
make retriever  # Generates a compatible retriever using create/create_hansard_retriever.py
```

Both targets will:
- Ensure the Python virtual environment is set up and dependencies are installed
- Use the unified project requirements.txt for consistency
- Output results to the `create/output/` directory

This workflow ensures that your retrievers are always in sync with your vector store schema and configuration. See the `create/` directory for template scripts tailored to Hansard.

### User Guide
- [User Interface Guide](docs/user-guide/interface.md)
- [Querying Guide](docs/user-guide/querying.md)
- [Using Citations](docs/user-guide/citations.md)
- [Feedback System](docs/user-guide/feedback.md)

## Project Status
This project is under active development. See our [roadmap](docs/development/roadmap.md) for planned features and improvements.

## Contributing
We welcome contributions! Please see our [contributing guidelines](docs/development/contributing.md) for more information.

## License
[Add license information here]

## Contact
[Add contact information here]