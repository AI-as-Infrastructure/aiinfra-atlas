# ATLAS Project

## Overview
ATLAS: Analysis and Testing of Language Models for Archival Systems is a test harness for the evaluation of Large Language Model (LLM) Retrieval Augmented Generation (RAG) for Humanities & Social Science (HASS) research. ATLAS is a deliverable of the [AI as Infrastructure (AIINFRA)](https://aiinfra.anu.edu.au) project. AIINFRA's primary goal is to develop an evaluation framework for LLM RAG systems designed for historical research.

## Project Status
The project is under development and makes heavy use of AI coding support. 

## Environment Requirements

- **Python:** 3.10 (required for backend and all scripts)
- **Node.js:** 22.14.0 (required for frontend; enforced via .nvmrc and package.json)
- **requirements.lock** is used at build time. The repo version could well have been generated on a Linux GPU-based system. Delete the file and run ```make l``` if necessary for your system.


## Core Components
ATLAS is built using the following technologies:

- FastAPI
- Vue 3
- Vite
- Chroma DB
- LangChain
- OpenTelemetry
- Phoenix: (Optional) 

Other dependencies include: Python virtual environments (`venv`), NVM, Sentence Transformers for embeddings, and various optional LLM providers (OpenAI, Anthropic, Ollama, etc.).

## Quick Start

1. Clone the repository.
2. Install Git LFS and pull the default vector store:
   ```bash
   git lfs install
   git lfs pull
   ```
3. Rename .env.template to .env.development and update the settings.
4. Start the development server (dependencies will be installed automatically):

   ```bash
   # Terminal 1 - Backend (FastAPI + ChromaDB)
   make b

   # Terminal 2 - Frontend (Vue + Vite)
   make f
   ```
5. Access the frontend via http://localhost:5173
6. (Optional) To clean and reset your environment:
   ```bash
   make d
   ```

## Command Reference

ATLAS uses a simplified command structure for common operations. Here are the main commands:

### Development
- `make b` - Start backend development server
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
- `make l` - Generate requirements.lock
- `make c` - Check Python environment
- `make vs` - Create vector store
- `make r` - Generate retriever
- `make xs` - Create XML vector store

For detailed help on any command, use:
```bash
make help-<command>
# Example: make help-b
```

To see all available commands:
```bash
make help
```

### Default Vector Store Setup

ATLAS requires a vector store for semantic search. You have two options:

1. **Use Mean Pooling (Default)**
   - No additional setup required
   - Uses a simple but effective embedding strategy
   - Suitable for basic testing and development

2. **Generate Custom Vector Store**
   - Recommended for production use
   - Provides better semantic search capabilities
   - Run the following command:
   ```bash
   make vs
   ```
   This will:
   - Generate embeddings using the BERT model
   - Create a vector store in `backend/targets/chroma_db/`
   - May take several minutes depending on your system

Note: The vector store generation process is optional but recommended for optimal performance. The default vector store included in the repository has been pre-generated using the create store process and includes fine-tuned embeddings. However, to use these fine-tuned embeddings, you'll need the corresponding fine-tuned model files in your models directory. If you don't have these files, the system will fall back to using mean pooling for embeddings.

### Vector Store & Retriever Generation Workflow

ATLAS provides a workflow for building new vector stores and generating compatible retrievers:

- The `create/` directory contains template scripts for generating vector stores (e.g., Hansard) and matching retriever classes.
- You can add new corpora (e.g., novels, newspapers) by copying and adapting these scripts.
- The following Makefile targets are available:

```bash
make vs      # Builds the vector store using create/create_hansard_store.py
make r       # Generates a compatible retriever using create/create_hansard_retriever.py
```

Both targets will:
- Ensure the Python virtual environment is set up and dependencies are installed
- Use the unified project requirements.txt for consistency
- Output results to the `create/output/` directory

This workflow ensures that your retrievers are always in sync with your vector store schema and configuration. 

## Additional Documentation

### Architecture and Configuration
- [Authentication](docs/authentication.md) - AWS Cognito setup and configuration
- [Configuration Guide](docs/configuration.md) - Environment files, API keys, and system configuration
- [Test Targets](docs/test_targets.md) - LLM configurations, vector store integration, and target management
- [Key Modules](docs/key_modules.md) - Core backend modules and their responsibilities

### Development and Deployment
- [Development Environment](docs/development.md) - Local development setup, workflow, and debugging
- [Staging Environment](docs/staging.md) - Local staging deployment for development and testing
- [Production Deployment](docs/production.md) - Complete production deployment guide with SSL, systemd services, and maintenance
- [Load Testing Framework](docs/load_testing.md) - Performance testing and optimization guidelines
- [Vector Store Creation](docs/create_store.md) - Building and managing vector stores and retrievers

### User Interface and Features
- [FAQ](frontend/src/views/FAQView.vue) - Frequently asked questions and system limitations

## License
- [License](LICENSE.md)